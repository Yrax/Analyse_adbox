import pytesseract
import os
import re
from io import BytesIO
from PIL import Image
from google.cloud import vision
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt # type: ignore

### 					   CLASSES						 ###

class Ad:
	name: str = '', 
	path: str = '', 
	image = None, # type : google.cloud.vision_v1.types.image_annotator.Image
	combined: bool = False, 
	imageBytes: bytes = None, 
	contentImage = None # type : proto.marshal.collections.repeated.RepeatedComposite
	noticed: bool = False 

### 					  FUNCTIONS						 ###


##		OCR function

def getContentImage(image, client, libName="Google-vision"):
	# Not recommended
	if libName == "Pytesseract":
		return pytesseract.image_to_string(image)
	
	if libName == "Google-vision":
		response = client.text_detection(image=image)
		try:
			if response.text_annotations :
				return response.text_annotations
		except response.error.message:
			raise Exception(response.error.message)		
	return 
	

##	  Open Image

def openSimpleImage(imagePath: str):
	if os.path.exists(imagePath):
		# return Image.open(imagePath)
		with open(imagePath, "rb") as image_file:
			content = image_file.read()
		return vision.Image(content = content)

def isSecondImage(ad: Ad):
	if ad.name[-5] == '2':
		return True
	return False

def combineImages(previousImagePath: str, currentImagePath: str):
	previousImage = Image.open(previousImagePath)
	currentImage = Image.open(currentImagePath)

	h = max(previousImage.height, currentImage.height)
	previousImage = previousImage.resize((previousImage.width, h))
	currentImage = currentImage.resize((currentImage.width, h))

	combined = Image.new("RGB", (previousImage.width + currentImage.width, h))
	combined.paste(previousImage, (0, 0))
	combined.paste(currentImage, (previousImage.width, 0))

	buffered = BytesIO()
	combined.save(buffered, format="JPEG")
	
	return buffered.getvalue()

def openImageCombined(ad: Ad, previousImage: str, previousImagePath: str,
					  notValid: list, notNoticed: list, isVertical: list):
	if previousImage in notNoticed:
		notNoticed.remove(previousImage)
	if previousImage in isVertical:
		isVertical.remove(previousImage)
	notValid.remove(previousImage)
	ad.imageBytes = combineImages(previousImagePath, ad.path)
	ad.image = vision.Image(content = ad.imageBytes)
	ad.combined = True

	return ad

def openImage(rep: str, ad: Ad, nbAd: int, notValid: list, notNoticed: list, isVertical: list):
	ad.imageBytes = None
	ad.combined = False
	ad.path = rep + '/' + ad.name

	if isSecondImage(ad):
		previousImage = ad.name[:-5] + '1' + ad.name[-4:]
		previousImagePath = rep + '/' + previousImage
		if not (previousImage in notValid):
			ad.noticed = True
		elif not os.path.exists(previousImagePath):
			raise ValueError(f'openImageCombined error: os.path.exists(previousImagePath) =')
		else:
			ad = openImageCombined(ad, previousImage, previousImagePath, notValid, notNoticed, isVertical)		
	else:	
		nbAd += 1
		ad.image = openSimpleImage(ad.path)

	return ad, nbAd


##	  Display (optional)

def displayImageAndText(ad: Ad):
	if ad.combined:
		image = Image.open(BytesIO(ad.imageBytes))
	else:
		image = Image.open(ad.path)
	image_np = np.array(image)
	print("\n****************************************************", ad.name, ad.contentImage[0].description, sep="\n")
	plt.figure(figsize = (10, 8)) 
	plt.imshow(image_np)
	plt.axis('off')
	plt.title(ad.name)
	plt.show()


##		Check Notice Position

def findNotice(contentImage):
	# 	 "L'abus d'alcool est dangereux pour la santé, à consommer avec modération"
	# or "L'abus d'alcool est dangereux pour la santé"
	notice = r"l[\'’\s]?abus d[\'’\s]?alcool est dangereux pour la sant[eé](, [aà] consommer avec mod[eé]ration)?"
	beginNotice = r"l[\'’\s]?abus"

	match = re.search(notice, contentImage[0].description, re.IGNORECASE)
	
	if match:
		for indexBlock, block in enumerate(contentImage[1:], start = 1):
			if re.search(beginNotice, block.description, re.IGNORECASE) :
				return indexBlock
	return -1


def blockNoticePositionY(contentImage, indexNotice):
	noticePositionY = [-1, -1, -1, -1]
	
	noticePositionY[0] = contentImage[indexNotice].bounding_poly.vertices[0].y
	noticePositionY[1] = contentImage[indexNotice].bounding_poly.vertices[1].y
	noticePositionY[2] = contentImage[indexNotice].bounding_poly.vertices[2].y
	noticePositionY[3] = contentImage[indexNotice].bounding_poly.vertices[3].y
		
	return noticePositionY

def checkNoticeDirection(noticePositionY, contentImage, currentIndex, checkDirection):
	# check position y for each point of block +/- 10 pixels (but percent is a better solution if it's possible)
	#		check position A.y : up left
	checkPosA = (
		noticePositionY[0] <= contentImage[currentIndex].bounding_poly.vertices[0].y + 10
		and noticePositionY[0] >= contentImage[currentIndex].bounding_poly.vertices[0].y - 10
	)
	# 	check position B.y : up right
	checkPosB = (
		noticePositionY[1] <= contentImage[currentIndex].bounding_poly.vertices[1].y + 10
		and noticePositionY[1] >= contentImage[currentIndex].bounding_poly.vertices[1].y - 10
	)
	# 	check position C.y : down right
	checkPosC = (
		noticePositionY[2] <= contentImage[currentIndex].bounding_poly.vertices[2].y + 10
		and noticePositionY[2] >= contentImage[currentIndex].bounding_poly.vertices[2].y - 10
	)
	# 	check position D.y : down left
	checkPosD = (
		noticePositionY[3] <= contentImage[currentIndex].bounding_poly.vertices[3].y + 10
		and noticePositionY[3] >= contentImage[currentIndex].bounding_poly.vertices[3].y - 10
	)
	
	# 	check if at least one check is not approximately equal to the starting position 
	if (
		not checkPosA 
		or not checkPosB 
		or not checkPosC 
		or not checkPosD
	):
		checkDirection = False
	
	return checkDirection

def isVerticalNotice(indexNotice: int, ad: Ad):
	# 7 because in "[L'abus] [d'alcool] [est] [dangereux] [pour] [la] [santé]" -> there is 7 blocks
	indexLastBlockNotice = indexNotice + 7 
	noticePositionY = blockNoticePositionY(ad.contentImage, indexNotice)
	for indexBlock in range(indexNotice, indexLastBlockNotice):
		checkDirection = checkNoticeDirection(noticePositionY, ad.contentImage, indexBlock, True)
		if not checkDirection:
			# displayImageAndText(ad)
			return True
	return False

def findNoticeBlock(blockNotice, contentImage, previousIndex):
	for indexBlock, block in enumerate(contentImage[previousIndex:], start = previousIndex):
		if re.search(blockNotice, block.description, re.IGNORECASE):
			return indexBlock
	return -1

def findValidNoticeInBlocks(notice, beginNoticePosY, beginNoticeIndex, contentImage):
	checkContinue = False
	dicoNoticeNotVertical = {}
	for index, block in enumerate(contentImage[beginNoticeIndex:], start = beginNoticeIndex):
		for blockNotice in notice[1:]:
			match = re.search(blockNotice, block.description, re.IGNORECASE)
			if match:
				# Check if Notice is Vertical
				checkDirection = checkNoticeDirection(beginNoticePosY, contentImage, index, True)
				if not checkDirection:
					checkDirection = False
					if not block.description in dicoNoticeNotVertical:
						dicoNoticeNotVertical[blockNotice] = False		
				# The following checks are missing:
				#		The verification of the word order in legal notice
				#		The verification that each word at Y-axis is among the allowed words
				#		The verification that a certain distance along the X-axis between each word is not exceeded
				
				else:
					dicoNoticeNotVertical[blockNotice] = True
				break

		for blockNotice in dicoNoticeNotVertical:
			if not dicoNoticeNotVertical[blockNotice]:
				checkContinue = True
		if not checkContinue:
			break

	for blockNotice in dicoNoticeNotVertical:
		if not dicoNoticeNotVertical[blockNotice]:
			return "Vertical"

	return "Found"


##		Check Notice If Exists 

def searchNoticeInCombinedImage(contentImage, previousIndex = 1):
	notice = [
		r"l[\'’\s]?abus",
		r'd[\'’\s]?alcool',
		r'est',
		r'dangereux',
		r'pour',
		r'la',
		r'sant[eé]'
	]
		
	while previousIndex < len(contentImage):
		beginNoticeIndex = findNoticeBlock(notice[0], contentImage, previousIndex)
		if beginNoticeIndex == -1:
			return "notNoticed"
		beginNoticePosY = blockNoticePositionY(contentImage, beginNoticeIndex)
		result = findValidNoticeInBlocks(notice, beginNoticePosY, beginNoticeIndex, contentImage)
		if result == "Found":
			break
		previousIndex += 1

	return result

def filterImagesNotNoticed(ad: Ad, notNoticed: list, isVertical: list, notValid: list):
	indexNotice = findNotice(ad.contentImage)
	# if ad is two images combined and notice not exist (not finished)
	if ad.combined and indexNotice == -1:
		research = searchNoticeInCombinedImage(ad.contentImage)
		if research != "Found":
			notValid.append(ad.name)
			if research == "notNoticed":
				notNoticed.append(ad.name)
			# there is no difference with the check of notNoticed or isVertical in this 'if'
			# because of missing checks in findValidNoticeInBlock
			if research == "Vertical":
				isVertical.append(ad.name)
			# displayImageAndText(ad)
		else:
			ad.noticed = True
	# if notice exist
	elif indexNotice != -1:
		if isVerticalNotice(indexNotice, ad):
			isVertical.append(ad.name)
			notValid.append(ad.name)
		else:
			ad.noticed = True
			# displayImageAndText(ad)
	else:
		notNoticed.append(ad.name)
		notValid.append(ad.name)
		# displayImageAndText(ad)
	

def browseImages(rep, images, nbAd, notNoticed, isVertical, notValid):
	client = vision.ImageAnnotatorClient()
	for imageName in images:
		ad = Ad()
		ad.name = imageName
		ad, nbAd = openImage(rep, ad, nbAd, notValid, notNoticed, isVertical)
		if ad.noticed:
			continue
		ad.contentImage = getContentImage(ad.image, client)
		filterImagesNotNoticed(ad, notNoticed, isVertical, notValid)

	return nbAd

### 							MAIN							 ###

repertory = "adbox-images"
images = sorted(os.listdir(repertory))
nbAd = 0
notValid = list()
notNoticed = list()
isVertical = list()

nbAd += browseImages(repertory, images, nbAd, notNoticed, isVertical, notValid)
print(nbAd, "publicités dont :")
print("\t->", len(notValid), "images sans la mention légale valide")
print("\t->", len(isVertical), "images avec la mention légale non valide")
print("\t->", len(notNoticed), "images sans la mention légale")

"""
Compte rendu d'exécution :

341 images en tout dont :
	330 étant des images sur l'alcool dont :
		12 images sont une suite d'une précédente image :
			En tout : 318 publicités sur l'alcool

les publicités sur l'alcool sans la mention par Google Vision qui sont en fait avec la mention valide :
	3027971.jpg :
		Google Vision lit "Cabus d'alcool est dangereux pour la santé". Comme on cherche à vérifier
		si une mention légale existe dans une image avec l'exacte même formule que celle écrit dans
		le texte de loi, j'estime que mettre une fonction de recherche textuelle approximative
		peut peut être créer des problèmes par la suite mais il faudrait en parler directement
		avec l'équipe qui a envoyer le ticket.
	
	3592291.jpg, 3592321.jpg (elles ont le même problème) :
		Sur l'image il est écrit ceci présenté de la forme et position suivante :
		"
		L'ABUS D'ALCOOL EST DANGEREUX POUR LA SANTÉ.
				À CONSOMMER AVEC MODÉRATION
		"
		Comme le 'É' de "MODÉRATION" est pile sous le 'X' de "DANGEREUX", l'accent du 'É' est lu
		par Google Vision comme étant une virgule sur la ligne d'au dessus.
		Ainsi Google Vision renvoi ce texte :
		"
		L'ABUS D'ALCOOL EST DANGEREUX, POUR LA SANTÉ.
				À CONSOMMER AVEC MODERATION
		"
		Je pense aussi que c'est parce que l'écart entre les deux lignes est un peu trop faible en plus 
		d'avoir la malchance que l'accent arrive pile tout proche de la fin du 'X' visuellement.

	-> 3/318 (0.94 %)

les publicités sur l'alcool :
	sans la mention légale valide :
		-> 40/318 (12.58 %)
	dont :
		avec la mention légale vertical :
			-> 10/318 (3.14 %)
		sans la mention légale :
			-> 30/318 (9.43 %)

(
	Plus de la moitié des images ne sont pas correctement reconnu par Pytesseract, j'ai au final
	très vite abandonné mes tests avec. Bien qu'il soit encore présent dans le code, il n'y a plus de
	fonctions permettant d'essayer toutes les images avec (je voulais les refaire mais je n'ai pas eu
	le temps)

	ce n'est pas de l'alcool :
		2677001.jpg
		2771591.jpg
		2771671.jpg
		3024451.jpg
		3169111.jpg
		3441881.jpg
		4007301.jpg
		4188981.jpg
		4247661.jpg
		4278801.jpg
		4278802.jpg

		-> 11/341
)
"""