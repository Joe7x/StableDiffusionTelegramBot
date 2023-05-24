from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image, ImageDraw, ImageFont
import torch
import os
import re
import random
import psutil
import GPUtil
import platform
import threading
import asyncio
import time
import datetime
import logging
import sys
import cpuinfo
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
import json
from zipfile import ZipFile
from cryptography.fernet import Fernet
import glob
import base64, hashlib
sys.argv.append('--lowvram')
sys.argv.append('--opt-split-attention')

#change values in conf.json file
conf_location = "conf.json"

#Do not change, parameters are read from conf file
botUsername = None
bot_token = None
botErrorMessage = None
bot_start_message = None
default_n_prompt = None
conf_file = None
admins = None
models = None
model_indexToUse = None
bot_permission_denied_message = None


logging.basicConfig(
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	level=logging.INFO
)
try:
	with open(conf_location, 'r') as file:
		conf_file = json.load(file)
		bot_token = str(conf_file.get("token"))
		default_n_prompt = str(conf_file.get("default_n_prompt"))
		admins = conf_file.get("admins")
		models = conf_file.get("models").get("model_locations")
		model_indexToUse = conf_file.get("models").get("model_index_to_use")
		botUsername = "@"+str(conf_file.get("bot_username"))
		botErrorMessage = str(conf_file.get("bot_error_message"))
		bot_start_message = str(conf_file.get("bot_start_message"))
		bot_permission_denied_message = str(conf_file.get("bot_permission_denied_message"))
except Exception as e:
	print(e)
async def image_grid(txt, imgs, rows, cols):
	assert len(imgs) == rows * cols
	w, h = imgs[0].size
	grid = Image.new('RGB', size=(cols * w, rows * h))
	font_path = r"./open-sans/OpenSans-Regular.ttf"
	fnt = ImageFont.truetype(font_path, size=24)
	d = ImageDraw.Draw(grid)
	for i, img in enumerate(imgs):
		grid.paste(img, box=(i % cols * w, i // cols * h))
		d.multiline_text((i % cols * w, i // cols * h + h-28), txt[i], font=fnt, fill=(255, 255, 255))
	return grid
normal = StableDiffusionPipeline.from_pretrained(str(models[model_indexToUse]), torch_dtype=torch.float16)
normal.scheduler = DPMSolverMultistepScheduler.from_config(normal.scheduler.config)
normal = normal.to("cuda")
normal.enable_attention_slicing()
normal.safety_checker = lambda images, **kwargs: (images, False)

async def get_values(txt):
	lst = []
	tempList = []
	lowestIndex = 9999999999
	strfindList = [":negative:",":steps:",":seed:",":gscale:",":size:"]
	output = ["", 15, -1, 10, 512, 512,"", 9999999999] #[nprompt, steps, seed, gscale, w, h, captiontosend, lowest index]
	for i in range(len(strfindList)):
		try:
			ind = 9999999999
			try:
				ind = txt.index(strfindList[i])
			except ValueError as e:
				print(e)
			if(ind < 9999999999):
				lst.append([strfindList[i],ind])
			if(ind < lowestIndex):
				lowestIndex = ind
		except Exception as e:
			print(e)
		continue
	output[7] = int(lowestIndex)
	sorted_li = sorted(lst, key=lambda x:x[1])
	size = len(sorted_li)
	for i in range(size):
		if(i+1<size):
			tempList.append([sorted_li[i][0],txt[sorted_li[i][1]+len(sorted_li[i][0]):sorted_li[i+1][1]]])
		else:
			tempList.append([sorted_li[i][0],txt[sorted_li[i][1]+len(sorted_li[i][0]):9999999999]])
	for i in range(len(tempList)):
		value = tempList[i][0]
		txt2 = tempList[i][1]
		if(value == ":negative:"):
			try:
				output[0] = str(txt2)
			except Exception as e:
				output[0] = ""
		elif(value == ":steps:"):
			try:
				step = int(txt2)
				if(step < 1):
					step = 1
				elif(step > 30):
					step = 30
				output[1] = step
			except Exception as e:
				output[1] = 15
		elif(value == ":seed:"):
			try:
				seed = int(txt2)
				if(seed < 1):
					seed = random.randint(1,4294967295)
				if(seed > 4294967295):
					seed = random.randint(1,4294967295)
				output[2] = seed
			except Exception as e:
				output[2] = random.randint(1,4294967295)
		elif(value == ":gscale:"):
			try:
				gscale = int(txt2)
				if(gscale < 1):
					gscale = 1
				if(gscale > 20):
					gscale = 20
				output[3] = gscale
			except Exception as e:
				output[3] = 10
		elif(value == ":size:"):
			w = 0
			h = 0
			captionToSend = ""
			try:
				index = txt2.index("x")
				w = int(txt2[0:index])
				h = int(txt2[index+1:])
			except Exception as e:
				w = 512
				h = 512
			if(w%8 != 0):
				w = w-w%8
			if(h%8 != 0):
				h = h-h%8
			if(w < 0 or h<0 or ((w*h)>(512*512))):
				captionToSend = str(w)+"x"+str(h) + " Too big or small, resized to default. "
				w=512
				h=512
			output[4] = w
			output[5] = h
			output[6] = captionToSend
		else:
			print("Error! Expected :negative:,:steps:,:seed:,:gscale: or :size: but got:" +str(value))
	if(output[2] < 1):
		output[2] = random.randint(1,4294967295)
	return output
async def gMulti(update: Update, context: ContextTypes.DEFAULT_TYPE):
	try:
		g1 = False
		g4 = False
		g9 = False
		gridAmount = 0
		gridX = 0
		gridY = 0
		chat_id = update.effective_message.chat_id
		txt = update.message.text
		if(txt.startswith("/pic")):
			txt = txt[len("/pic"):]
			g1 = True
			g4 = False
			g9 = False
		if(txt.startswith("/g9")):
			txt = txt[len("/g9"):]
			gridAmount = 9
			gridX = 3
			gridY = 3
			g1 = False
			g9 = True
			g4 = False
		if(txt.startswith("/g4")):
			txt = txt[len("/g4"):]
			gridAmount = 4
			gridX = 2
			gridY = 2
			g4 = True
			g1 = False
			g9 = False
		if(txt.startswith(str(botUsername))):
			txt = txt[len(str(botUsername)):]
		if(txt == "" or txt == str(botUsername)):
			await update.effective_message.reply_text(bot_start_message)
			return True
		if(g4 or g9):
			try:
				if(admins.index(chat_id) >=0):
					print("Access Granted to user with chat_id:" +str(chat_id))
				else:
					await update.effective_message.reply_text(bot_permission_denied_message)
					return False
			except Exception as e:
				await update.effective_message.reply_text(bot_permission_denied_message)
				print(e)
				return False
		print("chat_id:"+ str(chat_id))
		print("txt:"+str(txt))
		get = await get_values(txt)
		print(get)
		p_prompt = txt[:get[7]]
		n_prompt = get[0]
		step = get[1]
		seed = get[2]
		gscale = get[3]
		w = get[4]
		h = get[5]
		captionToSend = get[6]
		p_prompt = p_prompt.strip()
		global default_n_prompt
		if(n_prompt == "-"):
			n_prompt = ""
		elif(n_prompt == ""):
			n_prompt = default_n_prompt
		n = step
		g = gscale
		imgs = []
		txt = []
		firstSeed = seed
		if(g1):
			generator = torch.Generator("cuda").manual_seed(seed)
			image = normal(p_prompt, negative_prompt=n_prompt, num_inference_steps=n, width=w, height=h, guidance_scale=g, generator=generator).images[0]
			image.save(f"output/"+str(chat_id)+".png", "PNG")
		elif(g9 or g4):
			for i in range(gridAmount):
				generator = torch.Generator("cuda").manual_seed(seed)
				image = normal(p_prompt, negative_prompt=n_prompt, num_inference_steps=n, width=w, height=h, guidance_scale=g, generator=generator).images[0]
				imgs.append(image)
				txt.append(f"seed={seed}")
				#image.save(f"output/image-{i}.jpg")
				seed += 1
			grid = await image_grid(txt, imgs, gridX, gridY)
			grid.save(f"output/"+str(chat_id)+".png", "PNG")
		else:
			await update.effective_message.reply_text(bot_start_message)
			return True
		kuva = open("./output/"+str(chat_id)+".png","rb")
		captionToSend = captionToSend+ str(p_prompt)+" :negative: "+ n_prompt+" :steps: "+str(n)+ " :seed: "+ str(firstSeed)+" :gscale: "+ str(g)+" :size: "+ str(w)+ "x"+str(h)
		len1 = len(captionToSend)
		if(len1> 1000):
			over = len1-1000
			print("Caption too big!")
			captionToSend = "..."+captionToSend[over+len("..."):]
			print(captionToSend)
		await context.bot.send_photo(chat_id, photo=kuva,caption=captionToSend)
		try:
			os.remove("./output/"+str(chat_id)+".png")
		except Exception as e:
			print("Error! could not delete file!")
			print(e)
	except Exception as e:
		await update.effective_message.reply_text(botErrorMessage)
		print(e)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await context.bot.send_message(chat_id=update.effective_chat.id, text=bot_start_message)
async def sdefault(update: Update, context: ContextTypes.DEFAULT_TYPE):
	try:
		chat_id = update.effective_message.chat_id
		if(admins.index(chat_id) >=0):
			txt = update.message.text
			if(txt.startswith("/set_default_n_prompt")):
				txt = txt[22:]
			temp = "/set_default_n_prompt"+str(botUsername)
			if(txt.startswith(temp)):
				l = len(temp)
				txt = txt[l:]
			global default_n_prompt
			default_n_prompt = txt
			await update.effective_message.reply_text("OK set default_n_prompt to:" + str(default_n_prompt))
			print("User with chatid:"+ str(chat_id) + " set default n prompt to:"+default_n_prompt)
			return True
		else:
			await update.effective_message.reply_text("Could not set n_prompt, Permission denied")
			print("User tried to set_default_n_prompt without being an admin! chatid:"+ str(chat_id))
			return False
	except Exception as e:
		await update.effective_message.reply_text("Could not set n_prompt, Permission denied")
		return False
async def gdefault(update: Update, context: ContextTypes.DEFAULT_TYPE):
	txtToSend = str(default_n_prompt)
	await update.effective_message.reply_text(txtToSend)

startTime = time.time()
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
	try:
		chat_id = update.effective_message.chat_id
		uptime = str(datetime.timedelta(seconds=int(time.time()-startTime)))
		gpus = GPUtil.getGPUs()
		gpuload = gpus[0].load*100.0
		svmem = psutil.virtual_memory()
		swap = psutil.swap_memory()
		div = 1024*1024
		txt = "uptime: "+str(uptime)+" "+ str(cpuinfo.get_cpu_info()['brand_raw'])+") @ "+str(psutil.cpu_freq().max)+" total usage: "+str(psutil.cpu_percent())+ "% GPU: "+str(gpus[0].name)+ " usage: " + str(gpuload)+ "% RAM: total: "+str(int(svmem.total/div)) + "MiB available: "+str(int(svmem.available/div))+"MiB used: "+str(int(svmem.used/div))+ "MiB usage: "+str(svmem.percent) + "% SWAP memory total: "+ str(int(swap.total/div))+ "MiB free: "+str(int(swap.free/div))+"MiB used: "+str(int(swap.used/div))+"MiB usage: " + str(swap.percent)+"%"
		await update.effective_message.reply_text(txt)
		print("User: "+str(chat_id)+" generated statistics:"+str(txt))
	except Exception as e:
		await update.effective_message.reply_text("Error generating statistics")
		print("Error generating statistics!")
def run():
	start_handler = CommandHandler('start', start)
	img_handler = CommandHandler('pic', gMulti)
	status_handler = CommandHandler('status', status)
	set_n_prompt = CommandHandler('set_default_n_prompt', sdefault)
	get_n_prompt = CommandHandler('get_default_n_prompt', gdefault)
	generate9 = CommandHandler('g9', gMulti)
	generate4 = CommandHandler('g4', gMulti)
	application.add_handler(start_handler)
	application.add_handler(img_handler)
	application.add_handler(status_handler)
	application.add_handler(set_n_prompt)
	application.add_handler(get_n_prompt)
	application.add_handler(generate9)
	application.add_handler(generate4)
	print("\nBot Started " + time.asctime() + "\n")
	application.run_polling()
	print("\nBot Shutdown " + time.asctime()+ "\n")
application = ApplicationBuilder().token(str(bot_token)).build()
run()
