#!/usr/bin/python
# -*- coding: utf-8 -*-

## Made by Psycho - 2018 ##

import settings

import codecs
import json
import os
import paho.mqtt.client as mqtt
import paho.mqtt.publish as mqttPublish
import sys
from threading import Timer
import time
if settings.USE_LEDS:
	from pixels import Pixels, pixels
	from alexa_led_pattern import AlexaLedPattern
	from google_home_led_pattern import GoogleHomeLedPattern
import utils

import logging

logging.basicConfig(
	format='%(asctime)s [%(threadName)s] - [%(levelname)s] - %(message)s',
	level=logging.INFO,
	filename='logs.log',
	filemode='w'
)

# psycho intents

OPEN_RECIPE 				= 'hermes/intent/Psychokiller1888:openRecipe'
INGREDIENTS 				= 'hermes/intent/Psychokiller1888:ingredients'
PREVIOUS_STEP 				= 'hermes/intent/Psychokiller1888:previousStep'
REPEAT_STEP 				= 'hermes/intent/Psychokiller1888:repeatStep'
ACTIVATE_TIMER 				= 'hermes/intent/Psychokiller1888:activateTimer'

# Allo intents

NEXT_STEP 					= 'hermes/intent/Pierrot-app:nextStep'
GET_FOOD	 				= 'hermes/intent/Pierrot-app:getFoodRequest'
ASK_FOR_TIP	 				= 'hermes/intent/Pierrot-app:askForTip'
# PRODUCT_AGE	 				= 'hermes/intent/Pierrot-app:getProductAge'
# EATING_DATE 					= 'hermes/intent/Pierrot-app:getFoodRequest'
# GET_FOOD_COOK_NOW 			= 'hermes/intent/Pierrot-app:getFoodAndCookNow'
# GET_FOOD_KEEP 				= 'hermes/intent/Pierrot-app:getFoodAndKeep'
COOK_NOW_OR_KEEP			= 'hermes/intent/Pierrot-app:nowOrLater'
VALIDATE_QUESTION			= 'hermes/intent/Pierrot-app:validateQuestion'
INVALIDATE_QUESTION			= 'hermes/intent/Pierrot-app:invalidateQuestion'
START_RECIPE				= 'hermes/intent/Pierrot-app:startRecipe'
CANCEL						= 'hermes/intent/Pierrot-app:cancelSession'

# asr and tts

HERMES_ON_HOTWORD 			= 'hermes/hotword/default/detected'
HERMES_START_LISTENING 		= 'hermes/asr/startListening'
HERMES_SAY 					= 'hermes/tts/say'
HERMES_CAPTURED 			= 'hermes/asr/textCaptured'
HERMES_HOTWORD_TOGGLE_ON 	= 'hermes/hotword/toggleOn'

recipe_ingredients = [
	'pomme',
	'pommes',
	'courgette',
	'courgettes',
	'oeufs',
	'oeuf'
	]

tips_list_from_paprika = {
	'pommes': {
		'un crumble aux pommes': './recipes/fr/pomme-crumble.json'
	},
	'pomme': {
		'un crumble aux pommes': './recipes/fr/pomme-crumble.json'
	},
	'courgette': {
		'des pates aux courgettes': './recipes/fr/courgettes-pates.json'
	},
	'courgettes': {
		'des pates aux courgettes': './recipes/fr/courgettes-pates.json'
	},
	'orange': {
		'de la confiture d\'orange au thym': './recipes/fr/orange-confiture.json',
		'une glace à l\'orange': './recipes/fr/orange-glace.json'
	},
	'oranges': {
		'de la confiture d\'orange au thym': './recipes/fr/orange-confiture.json',
		'une glace à l\'orange': './recipes/fr/orange-glace.json'
	}
}

tips_list_from_marin = {
	'orange': {
		'une huile essentielle d\'orange': './recipes/fr/orange-huile.json'
	},
	'oranges': {
		'une huile essentielle d\'orange': './recipes/fr/orange-huile.json'
	}
}

def onConnect(client, userData, flags, rc):
	mqttClient.subscribe(OPEN_RECIPE)
	mqttClient.subscribe(NEXT_STEP)
	mqttClient.subscribe(INGREDIENTS)
	mqttClient.subscribe(PREVIOUS_STEP)
	mqttClient.subscribe(REPEAT_STEP)
	mqttClient.subscribe(ACTIVATE_TIMER)

	mqttClient.subscribe(GET_FOOD)
	mqttClient.subscribe(ASK_FOR_TIP)
	# mqttClient.subscribe(PRODUCT_AGE)
	# mqttClient.subscribe(EATING_DATE)
	# mqttClient.subscribe(GET_FOOD_COOK_NOW)
	# mqttClient.subscribe(GET_FOOD_KEEP)
	mqttClient.subscribe(COOK_NOW_OR_KEEP)
	mqttClient.subscribe(VALIDATE_QUESTION)
	mqttClient.subscribe(INVALIDATE_QUESTION)
	mqttClient.subscribe(START_RECIPE)
	mqttClient.subscribe(CANCEL)

	mqttClient.subscribe(HERMES_ON_HOTWORD)
	mqttClient.subscribe(HERMES_START_LISTENING)
	mqttClient.subscribe(HERMES_SAY)
	mqttClient.subscribe(HERMES_CAPTURED)
	mqttClient.subscribe(HERMES_HOTWORD_TOGGLE_ON)
	mqttPublish.single('hermes/feedback/sound/toggleOn', payload=json.dumps({'siteId': 'default'}), hostname='127.0.0.1', port=1883)

def onMessage(client, userData, message):
	global lang

	intent = message.topic
	payload = json.loads(message.payload)


	if intent == HERMES_ON_HOTWORD:
		last_hotword = utils.read_file("hotword.txt")
		current_hotword = payload['modelId'].encode('utf-8')
		if last_hotword != current_hotword:
			utils.write_to_file("hotword.txt", current_hotword)

		if settings.USE_LEDS:
			pixels.wakeup()
		return

	elif intent == HERMES_SAY:
		if settings.USE_LEDS:
			pixels.speak()
		return

	elif intent == HERMES_CAPTURED:
		if settings.USE_LEDS:
			pixels.think()
		return

	elif intent == HERMES_START_LISTENING:
		if settings.USE_LEDS:
			pixels.listen()
		return

	elif intent == HERMES_HOTWORD_TOGGLE_ON:
		if settings.USE_LEDS:
			pixels.off()
		return

	global recipe, currentStep, timers, confirm, sessionId, product, tipIndex, fromIntent

	sessionId = payload['sessionId']

	##### TODO stabiliser avant réactivation

	if intent == OPEN_RECIPE:
		print("INTENT : OPEN_RECIPE")
		if 'slots' not in payload:
			error(sessionId)
			return

		slotRecipeName = payload['slots'][0]['value']['value'].encode('utf-8')

		if recipe is not None and currentStep > 0:
			if confirm <= 0:
				confirm = 1
				endTalk(sessionId, text=lang['warningRecipeAlreadyOpen'])
				return
			else:
				for timer in timers:
					timer.cancel()

				timers = {}
				confirm = 0
				currentStep = 0

		if any(product.lower() in ingredients for ingredients in tips_list_from_paprika):
			recipe_nb = len(tips_list_from_paprika[product.lower()])
			if recipe_nb == 1:
				for recipe in tips_list_from_paprika[product.lower()]:
					continueSession(sessionId, "j'ai trouvé une astuce: "+ recipe +". Tu veux faire ça ?", intents=['Pierrot-app:validateQuestion'] )
			elif recipe_nb == 2:
				askForTwoTips(getTipList)
		else:
			endTalk(sessionId, text=lang['noTipsForProduct'])
		fromIntent = "OPEN_RECIPE"

	if intent == NEXT_STEP:
		print("INTENT : NEXT_STEP")
		if recipe is None:
			print("recipe is None NEXT_STEP")
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			print("recipe is NOT None NEXT_STEP")
			if str(currentStep + 1) not in recipe['steps']:
				endTalk(sessionId, text=lang['recipeEnd'])
			else:
				currentStep += 1
				step = recipe['steps'][str(currentStep)]

				ask = False
				if type(step) is dict and currentStep not in timers:
					ask = True
					step = step['text']

				endTalk(sessionId, text=lang['nextStep'].format(step))
				if ask:
					say(text=lang['timerAsk'])
		fromIntent = "NEXT_STEP"

	elif intent == INGREDIENTS:
		print("INTENT : INGREDIENTS")
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			ingredients = ''
			for ingredient in recipe['ingredients']:
				ingredients += u"{}. ".format(ingredient)

			endTalk(sessionId, text=lang['neededIngredients'].format(ingredients))
		fromIntent = "INGREDIENTS"

	elif intent == PREVIOUS_STEP:
		print("INTENT : PREVIOUS_STEP")
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			if currentStep <= 1:
				endTalk(sessionId, text=lang['noPreviousStep'])
			else:
				currentStep -= 1
				step = recipe['steps'][str(currentStep)]

				ask = False
				timer = 0
				if type(step) is dict and currentStep not in timers:
					ask = True
					timer = step['timer']
					step = step['text']

				endTalk(sessionId, text=lang['previousStepWas'].format(step))
				if ask:
					say(text=lang['hadTimerAsk'].format(timer))
		fromIntent = "PREVIOUS_STEP"

	elif intent == REPEAT_STEP:
		print("INTENT : REPEAT_STEP")
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			if currentStep <= 1:
				ingredients = ''
				for ingredient in recipe['ingredients']:
					ingredients += u"{}. ".format(ingredient)

				endTalk(sessionId, text=lang['neededIngredients'].format(ingredients))
			else:
				step = recipe['steps'][str(currentStep)]
				endTalk(sessionId, text=lang['repeatStep'].format(step))
		fromIntent = "REPEAT_STEP"

	elif intent == ACTIVATE_TIMER:
		print("INTENT : ACTIVATE_TIMER")
		if recipe is None:
			endTalk(sessionId, text=lang['noTimerNotStarted'])
		else:
			step = recipe['steps'][str(currentStep)]

			if type(step) is not dict:
				endTalk(sessionId, text=lang['notTimerForThisStep'])
			elif currentStep in timers:
				endTalk(sessionId, text=lang['timerAlreadyRunning'])
			else:
				timer = Timer(int(step['timer']), onTimeUp, args=[currentStep, step])
				timer.start()
				timers[currentStep] = timer
				endTalk(sessionId, text=lang['timerConfirm'])
		fromIntent = "ACTIVATE_TIMER"

	elif intent == GET_FOOD:
		print("INTENT : GET_FOOD")
		sayNoSession(lang['searching'])
		asTalk = False
		product = payload["slots"][0]["rawValue"]
		# If product asked exist in my list 
		if any(product.lower() in ingredients for ingredients in getTipList()):
			if asTalk is False:
				asTalk = True
				if lastIntent == "ASK_FOR_TIP" or getAssistant() == "marin":
					readTipsProposition()
				else:
					continueSession(sessionId=sessionId, text=lang['cookNowOrKeep'].format(product), intents=['Pierrot-app:nowOrLater'])
		else:
			endTalk(sessionId, text=lang['noTipsForProduct'])
		fromIntent = "GET_FOOD"

	elif intent == ASK_FOR_TIP:
		print("INTENT : ASK_FOR_TIP")
		if product in getTipList():
			continueSession(sessionId=sessionId, text=lang['tipFor'].format(product), intents=['Pierrot-app:validateQuestion', 'Pierrot-app:invalidateQuestion'])
		else:
			continueSession(sessionId=sessionId, text=lang['tipForWhat'], intents=['Pierrot-app:getFoodRequest'])
		fromIntent = "ASK_FOR_TIP"


	# elif intent == GET_FOOD_COOK_NOW:
	# 	product = payload['slots'][0]['value']['value'].encode('utf-8')
	# 	if any(product.lower() in ingredients for ingredients in recipe_ingredients):
	# 		# endTalk(sessionId=sessionId, text=lang['startRecipe'].format(food), intents=['openRecipe'])
	# 		readRecipe(sessionId, product, payload)
	# 	else:
	# 		endTalk(sessionId, text=lang['recipeNotFound'])

	elif intent == COOK_NOW_OR_KEEP:
		print("INTENT : COOK_NOW_OR_KEEP")
		# if recipe is None:
		# 	endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		# else:
		readTipsProposition()
		fromIntent = "COOK_NOW_OR_KEEP"


	elif intent == VALIDATE_QUESTION:
		print("INTENT : VALIDATE_QUESTION")
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		# elif fromIntent == "COOK_NOW_OR_KEEP":
		else:
			if currentStep != 0:
				currentStep += 1
				step = recipe['steps'][str(currentStep)]

				ask = False
				if type(step) is dict and currentStep not in timers:
					ask = True
					step = step['text']

				endTalk(sessionId, text=lang['nextStep'].format(step))
			else:
				ingredients = ''
				for ingredient in recipe['ingredients']:
					ingredients += u"{}. ".format(ingredient)

				endTalk(sessionId, text=lang['neededIngredients'].format(ingredients))
		# elif fromIntent == "ASK_FOR_TIP" or fromIntent == "GET_FOOD":
		# 	readTipsProposition()
		fromIntent = "VALIDATE_QUESTION"

	elif intent == INVALIDATE_QUESTION:
		print("INTENT : INVALIDATE_QUESTION")
		print("tupIndex : ", tipIndex)
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			if tipIndex == 1:
				tipIndex += 1
				askForTwoTips(getTipList()[product.lower()])
			else:
				endTalk(sessionId, text=lang['noMoreTip'])
		fromIntent = "INVALIDATE_QUESTION"

	elif intent == START_RECIPE:
		print("INTENT : START_RECIPE")
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			currentStep += 1
			step = recipe['steps'][str(currentStep)]

			ask = False
			if type(step) is dict and currentStep not in timers:
				ask = True
				step = step['text']

			endTalk(sessionId, text=lang['nextStep'].format(step))
			if ask:
				say(text=lang['timerAsk'])
		fromIntent = "START_RECIPE"


	elif intent == CANCEL:
		if settings.USE_LEDS:
			pixels.off()
		error(sessionId)
		mqttClient.loop_stop()
		mqttClient.disconnect()
		running = False

def readTipsProposition():
	if any(product.lower() in ingredients for ingredients in getTipList()):
		tip_nb = len(getTipList()[product.lower()])
		if tip_nb == 1:
			for tip in getTipList()[product.lower()]:
				tipPath = getTipList()[product.lower()][tip]
				getRecipe(sessionId, tipPath)
				continueSession(sessionId, "j'ai trouvé une astuce: "+ tip +". Tu veux faire ça ?", intents=['Pierrot-app:validateQuestion', 'Pierrot-app:invalidateQuestion'] )
		elif tip_nb == 2:
			askForTwoTips(getTipList()[product.lower()])
	else:
		endTalk(sessionId, text=lang['noTipsForProduct'])

def askForTwoTips(tipsList):
	for i, tip in enumerate(tipsList, start=1):
		tipPath = tipsList[tip]
		if i == 1 and tipIndex == 1:
			getRecipe(sessionId, tipPath)
			continueSession(sessionId, "j'ai trouvé deux astuces: la première "+ tip +". Tu veux faire ça ?", intents=['Pierrot-app:validateQuestion', 'Pierrot-app:invalidateQuestion'])
			# tipIndex += 1
		if i == 2 and tipIndex == 2:
			getRecipe(sessionId, tipPath)
			continueSession(sessionId, "et la deuxième "+ tip +". Tu veux faire ça ?", intents=['Pierrot-app:validateQuestion', 'Pierrot-app:invalidateQuestion'])
			# tipIndex +=1

def getTipList():
	hotword = utils.read_file("hotword.txt")
	if hotword == "paprika":
		return tips_list_from_paprika
	elif hotword == "marin":
		return tips_list_from_marin

def getAssistant():
	assistantName = utils.read_file("hotword.txt")
	return assistantName

def error(sessionId):
	endTalk(sessionId, lang['error'])

def continueSession(sessionId, text, intents):
	mqttClient.publish('hermes/dialogueManager/continueSession', json.dumps({
		'sessionId': sessionId,
		'text': text,
		'intentFilter': intents
	}))

def endTalk(sessionId, text):
	mqttClient.publish('hermes/dialogueManager/endSession', json.dumps({
		'sessionId': sessionId,
		'text': text
	}))

def say(text):
	mqttClient.publish('hermes/dialogueManager/startSession', json.dumps({
		'init': {
			'type': 'notification',
			'text': text
		}
	}))

def sayNoSession(text):
	mqttClient.publish('hermes/tts/say', json.dumps({
		'text' : text,
		'lang' : 'fr',
		'siteId' : 'default'
	}))

def nextStep(sessionId):
	mqttClient.publish(NEXT_STEP, json.dumps({
		"sessionId" : sessionId,
		"customData" : "null",
		"siteId" : "default",
		"input" : "étape suivante",
		"intent" : {
			"intentName" : "Pierrot-app:nextStep",
			"probability" : 1
			},
		"slots" : [ ]
	}))

def onTimeUp(*args, **kwargs):
	global timers
	wasStep = args[0]
	step = args[1]
	del timers[wasStep]
	say(text=lang['timerEnd'].format(step['textAfterTimer']))

def getRecipe(sessionId, tipPath):
	global recipe
	currentStep = 0
	file = codecs.open(tipPath, 'r', encoding='utf-8')
	string = file.read()
	file.close()
	recipe = json.loads(string)

	#time.sleep(2)

	recipeName = recipe['name'] if 'phonetic' not in recipe else recipe['phonetic']
	timeType = lang['cookingTime'] if 'cookingTime' in recipe else lang['waitTime']
	cookOrWaitTime = recipe['cookingTime'] if 'cookingTime' in recipe else recipe['waitTime']

	# continueSession(sessionId=sessionId, text=lang['recipeProposition'].format(recipeName), intents=['Pierrot-app:validateQuestion'])


mqttClient = None
product = None
leds = None
running = True
recipe = None
sessionId = None
startTip = False
lastIntent = ""
currentStep = 0
tipIndex = 1
timers = {}
confirm = 0
lang = ''

logger = logging.getLogger('Allo')
logger.addHandler(logging.StreamHandler())

if __name__ == '__main__':
	logger.info('...My Chef...')

	if settings.USE_LEDS:
		pixels.pattern = GoogleHomeLedPattern(show=pixels.show)
		pixels.off()

	try:
		file = codecs.open('./languages/{}.json'.format(settings.LANG), 'r', encoding='utf-8')
		string = file.read()
		file.close()
		lang = json.loads(string)
	except:
		logger.error('Error loading language file, exiting')
		sys.exit(0)

	mqttClient = mqtt.Client()
	mqttClient.on_connect = onConnect
	mqttClient.on_message = onMessage
	mqttClient.connect('localhost', 1883)
	logger.info(lang['appReady'])
	mqttClient.loop_start()
	try:
		while running:
			time.sleep(0.1)
	except KeyboardInterrupt:
		if sessionId is not None:
			error(sessionId)
		mqttClient.loop_stop()
		mqttClient.disconnect()
		running = False
	finally:
		logger.info(lang['stopping'])
