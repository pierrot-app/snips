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

NEXT_STEP 					= 'hermes/intent/Psychokiller1888:nextStep'
GET_FOOD	 				= 'hermes/intent/Pierrot-app:getFoodRequest'
PRODUCT_AGE	 				= 'hermes/intent/Pierrot-app:getProductAge'
EATING_DATE 				= 'hermes/intent/Pierrot-app:getFoodRequest'
# GET_FOOD_COOK_NOW 			= 'hermes/intent/Pierrot-app:getFoodAndCookNow'
GET_FOOD_KEEP 				= 'hermes/intent/Pierrot-app:getFoodAndKeep'
COOK_NOW_OR_KEEP			= 'hermes/intent/Pierrot-app:nowOrLater'
VALIDATE_QUESTION			= 'hermes/intent/Pierrot-app:validateQuestion'
START_RECIPE				= 'hermes/intent/Pierrot-app:startRecipe'
CANCEL						= 'hermes/intent/Pierrot-app:cancelSession'

# asr and tts

HERMES_ON_HOTWORD 			= 'hermes/hotword/default/detected'
HERMES_START_LISTENING 		= 'hermes/asr/startListening'
HERMES_SAY 					= 'hermes/tts/say'
HERMES_CAPTURED 			= 'hermes/asr/textCaptured'
HERMES_HOTWORD_TOGGLE_ON 	= 'hermes/hotword/toggleOn'

recipe_ingredients = [
	'pommes',
	'pomme',
	'courgette',
	'courgettes',
	'oeufs',
	'oeuf'
]

def onConnect(client, userData, flags, rc):
	mqttClient.subscribe(OPEN_RECIPE)
	mqttClient.subscribe(NEXT_STEP)
	mqttClient.subscribe(INGREDIENTS)
	mqttClient.subscribe(PREVIOUS_STEP)
	mqttClient.subscribe(REPEAT_STEP)
	mqttClient.subscribe(ACTIVATE_TIMER)

	mqttClient.subscribe(GET_FOOD)
	mqttClient.subscribe(PRODUCT_AGE)
	mqttClient.subscribe(EATING_DATE)
	# mqttClient.subscribe(GET_FOOD_COOK_NOW)
	mqttClient.subscribe(GET_FOOD_KEEP)
	mqttClient.subscribe(COOK_NOW_OR_KEEP)
	mqttClient.subscribe(VALIDATE_QUESTION)
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

	global recipe, currentStep, timers, confirm, sessionId, product

	sessionId = payload['sessionId']

	if intent == OPEN_RECIPE:
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

		# TODO changer cette condition par la prise en compte de l'ingredient dans le nom de la recette.
		if any(slotRecipeName.lower() in ingredients for ingredients in recipe_ingredients):
		# if os.path.isfile('./recipes/{}/{}.json'.format(settings.LANG, slotRecipeName.lower())):
			readRecipe(sessionId, slotRecipeName, payload)
		else:
			endTalk(sessionId, text=lang['recipeNotFound'])

	elif intent == NEXT_STEP:
		# print("recipe : ",recipe)
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
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

	elif intent == INGREDIENTS:
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
		else:
			ingredients = ''
			for ingredient in recipe['ingredients']:
				ingredients += u"{}. ".format(ingredient)

			endTalk(sessionId, text=lang['neededIngredients'].format(ingredients))

	elif intent == PREVIOUS_STEP:
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

	elif intent == REPEAT_STEP:
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

	elif intent == ACTIVATE_TIMER:
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

	elif intent == GET_FOOD:
		product = payload["slots"][0]["rawValue"]
		if any(product.lower() in ingredients for ingredients in recipe_ingredients):
			continueSession(sessionId=sessionId, text=lang['cookNowOrKeep'].format(product), intents=['Pierrot-app:nowOrLater'])
		else:
			endTalk(sessionId, text=lang['recipeNotFound'])

	# elif intent == GET_FOOD_COOK_NOW:
	# 	product = payload['slots'][0]['value']['value'].encode('utf-8')
	# 	if any(product.lower() in ingredients for ingredients in recipe_ingredients):
	# 		# endTalk(sessionId=sessionId, text=lang['startRecipe'].format(food), intents=['openRecipe'])
	# 		readRecipe(sessionId, product, payload)
	# 	else:
	# 		endTalk(sessionId, text=lang['recipeNotFound'])

	elif intent == COOK_NOW_OR_KEEP:
		readRecipe(sessionId, product, payload)

	elif intent == VALIDATE_QUESTION:
		if recipe is None:
			endTalk(sessionId, text=lang['sorryNoRecipeOpen'])
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

	elif intent == START_RECIPE:
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


	elif intent == CANCEL:
		if settings.USE_LEDS:
			pixels.off()
		error(sessionId)
		mqttClient.loop_stop()
		mqttClient.disconnect()
		running = False




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

def readRecipe(sessionId, slotRecipeName, payload):
	global recipe
	currentStep = 0
	file = codecs.open('./recipes/{}/{}.json'.format(settings.LANG, slotRecipeName.lower()), 'r', encoding='utf-8')
	string = file.read()
	file.close()
	recipe = json.loads(string)

	#time.sleep(2)

	recipeName = recipe['name'] if 'phonetic' not in recipe else recipe['phonetic']
	timeType = lang['cookingTime'] if 'cookingTime' in recipe else lang['waitTime']
	cookOrWaitTime = recipe['cookingTime'] if 'cookingTime' in recipe else recipe['waitTime']

	continueSession(sessionId=sessionId, text=lang['recipeProposition'].format(recipeName), intents=['Pierrot-app:validateQuestion'])


mqttClient = None
leds = None
running = True
recipe = None
sessionId = None
currentStep = 0
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
