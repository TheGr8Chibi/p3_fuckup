import math
import os
import sys
from collections import deque
import imutils

TS = False
TM = False
KNN = True

if TS:
    import pytesseract as pt

import cv2
import matplotlib.pyplot as plt
import numpy as np

MIN_CONTOUR_AREA = 100
RESIZED_IMAGE_WIDTH = 20
RESIZED_IMAGE_HEIGHT = 30
strFinalString = ""  # declare final string, this will have the final number sequence by the end of the program

class Tesseract:
    def __init__(self, img):
        self.img = img

    # Tesseract setup
    def getText(self):
        #Local Tesseract path
        pt.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        #Which characters to look for
        out_below = pt.image_to_string(self.img, config='-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --psm 10')
        print(out_below)

# Empty variables for the grayscale and binary arrays of the image
grayImg = None
binaryImg = None
binaryImg2 = None

#Convolution function
def convolute(img, filter):
    imgRow, imgCol = img.shape
    kernelRow, kernelCol = filter.shape
    output = np.zeros(img.shape)

    #Add padding to the image
    pad_height = kernelRow // 2
    pad_width = kernelCol // 2
    padded_image = np.zeros((imgRow + (2 * pad_height), imgCol + (2 * pad_width)))
    padded_image[pad_height:padded_image.shape[0] - pad_height, pad_width:padded_image.shape[1] - pad_width] = img

    for row in range(imgRow):
        for col in range(imgCol):
            output[row, col] = np.sum(filter * padded_image[row:row + kernelRow, col:col + kernelCol])
            output[row, col] /= filter.shape[0] * filter.shape[1]
    return output

#Gray scaling (Step 1)
def grayScale(img):

    print('Running gray scaling')
    height, width, channel = img.shape

    for i in range(height):
        for j in range(width):
            #Convert to grayscale
            r, g, b = img[i, j]
            px = r*0.1 + g*0.6 + b*0.3
            grayImg[i, j] = px
            #Convert to binary
            if px >= 90:
                binaryImg[i, j] = 255
                binaryImg2[i, j] = 0
            #Convert to inverted binary
            else:
                binaryImg[i, j] = 0
                binaryImg2[i, j] = 255

    #Save the images
    cv2.imwrite('grayImg.jpg', grayImg)
    cv2.imwrite('binaryImg2.jpg', binaryImg2)
    cv2.imwrite('binaryImg.jpg',binaryImg)
    plt.imshow(grayImg, cmap='gray')
    plt.title("Grayscale")
    plt.show()
    print('Completed')
    gaussianBlur(5, grayImg)

#Generate 5X5 gaussian kernel and apply filter (Step 2)
def gaussianBlur(size, img, sigma=1):
    print('Applying gaussian filter')
    kernel = np.zeros((size,size))
    img = img
    for x in range(0,size):
        for y in range(0,size):
            kernel[x,y] = 1/(np.sqrt(2 * np.pi * sigma ** 2)) * np.e ** (-x**2 + y**2/2*sigma**2)
    filteredImage = convolute(img, kernel)
    print('Completed')
    sobel(filteredImage)

#Apply sobel kernels to the filtered image (Step 3)
def sobel(img):
    print('Applying sobel kernel')
    imgRow, imgCol = img.shape
    angle = np.zeros(img.shape)

    Gx = np.array \
        ([[-1,0,1],
          [-2,0,2],
          [-1,0,1]])

    Gy = np.array \
        ([[1, 2, 1],
          [0, 0, 0],
          [-1,-2,-1]])

    GxOut = convolute(img, Gx)
    GyOut = convolute(img, Gy)

    #Calculate edge slope for each pixel
    for row in range(imgRow):
        for col in range(imgCol):
            angle[row, col] = np.arctan2(GyOut[row, col], GxOut[row, col])

    #Calculate edge magnitude
    G = np.sqrt(GxOut**2 + GyOut**2)

    #plt.imshow(G, cmap='gray')
    #plt.title("Sobel")
    #plt.show()
    print('Completed')
    non_max(G,angle)

#Non-maximum suppression (Step 4)
def non_max(img, angle):
    print('Applying non-maximum suppression')
    imgRow, imgCol = img.shape
    output = np.zeros(img.shape)

    angle = angle * 180. / np.pi
    angle[angle < 0] += 180

    for row in range(1,imgRow-1):
        for col in range(1,imgCol-1):
            q = 255
            r = 255

            if(0 <= angle[row,col] < 22.5) or (157.5 <= angle[row,col] <= 180):
                q = img[row,col+1]
                r = img[row,col-1]
            elif (22.5 <= angle[row,col] < 67.5):
                q = img[row+1,col-1]
                r = img[row-1,col+1]
            elif (67.5 <= angle[row,col] < 112.5):
                q = img[row+1,col]
                r = img[row-1,col]
            elif (112.5 <= angle[row,col] < 157.5):
                q = img[row-1,col-1]
                r = img[row+1,col+1]

            if(img[row,col] >= q) and (img[row,col] >= r):
                output[row,col] = img[row,col]
            else:
                output[row, col] = 0

    print('Completed')
    doubleThreshold(output)

    #plt.imshow(output, cmap='gray')
    #plt.title("Non-maximum suppression")
    #plt.show()

#Double thresholding (Step 5)
def doubleThreshold(img):
    print('Applying double threshold')
    row, col = img.shape
    weak = 25
    strong = 255
    output = np.zeros((row,col))

    lowThresholdRatio = 0.05
    highThresholdRatio = 0.2

    highThresh = img.max() * highThresholdRatio
    lowThresh = highThresh * lowThresholdRatio

    weakX, weakY = np.where((img <= highThresh) & (img >= lowThresh))
    strongX, strongY = np.where(img >= highThresh)

    output[strongX, strongY] = strong
    output[weakX, weakY] = weak
    #cv2.imwrite('non_max.jpg',output)

    print('Completed')
    trackEdge(output)

#Edge tracking (Step 6)
def trackEdge(img):
    print('Tracking edges')
    strong = 255
    weak = 25

    for row in range(1, img.shape[0]-1):
        for col in range(1, img.shape[1]-1):
            if (img[row,col] == weak):
                try:
                    if (img[row+1, col] == strong or img[row, col+1] == strong or img[row-1, col] == strong
                            or img[row, col-1] == strong or img[row+1, col+1] == strong
                            or img[row-1, col-1] == strong or img[row+1, col-1] == strong
                            or img[row-1, col+1] == strong):
                        img[row, col] = 255
                    else:
                        img[row, col] = 0
                except IndexError as e:
                    print("ERR")

    print('Completed')

    cv2.imwrite('edge.jpg',img)
    plt.imshow(img, cmap='gray')
    plt.title("Edge tracking")
    plt.show()

    detectPlate(img)

#License plate detection (Step 7)
def detectPlate(img):
    print('Detecting license plate')
    img = img.astype(np.uint8)
    contours = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = imutils.grab_contours(contours)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    cnt = None
    for c in contours:
        perimeter = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.05 * perimeter, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            print('Width: ' + str(w))
            print('Height: ' + str(h))
            aspectRatio = float(w) / h
            if aspectRatio >= 3.9 and aspectRatio <= 5.4:
                cnt = approx
                break
    if cnt is None:
        print('ERR - No license plate found')
        return None

    x, y, w, h = cv2.boundingRect(cnt)
    cv2.rectangle(binaryImg, (x, y), (x + w, y + h), (0, 255, 0), 2)

    nummerpladeFrame = binaryImg[y: y + h, x+10: x + w-5]
    nummerpladeFrameInv = binaryImg2[y: y + h, x+10: x + w-5]

    height = 50
    width = int(height * 4.75)
    dim = (width, height)
    #Resize image
    resized = cv2.resize(nummerpladeFrame, dim, interpolation=cv2.INTER_AREA)
    resizedInv = cv2.resize(nummerpladeFrameInv, dim, interpolation=cv2.INTER_AREA)
    plate = cv2.imwrite('plate.jpg', nummerpladeFrame)
    pl = cv2.imread('plate.jpg')
    print('Completed')

    #plt.imshow(resized, cmap='gray')
    #plt.title("Plate")
    #plt.show()

    if TS:
        ts = Tesseract(pl)
        ts.getText()
    else:
        if TM:
            createTemps(lt, num)
        print('Detecting characters')
        count(resized, resizedInv)

#Character segmentation (Step 8)
def count(img, imgInv):
    visited = np.zeros((img.shape[0], img.shape[1]))
    for x in range(0, img.shape[1]):
        for y in range(0, img.shape[0]):
            if img[y][x] == 0 and visited[y][x] != 1:
                append = True
                XYArray = []
                queue = deque([])
                grassFire(y, x, XYArray, append, img, imgInv, visited, queue)
            else:
                visited[y][x] = 1

    print(*letters)
    print('Completed')

letterArray = []
letters = []

def grassFire(y, x, XYArray, append, img, imgInv, visited, queue):
    try:
        if append == True:
            visited[y][x] = 1
            XYArray.append([x, y])
            queue.append([x, y])
        append = True

        if x + 1 < img.shape[1] and img[y][x + 1] == 0 and visited[y][x + 1] != 1:
            grassFire(y, x + 1, XYArray, append, img, imgInv, visited, queue)

        elif y + 1 < img.shape[0] and img[y + 1][x] == 0 and visited[y + 1][x] != 1:
            grassFire(y + 1, x, XYArray, append, img, imgInv,visited, queue)

        elif x > 0 and img[y][x - 1] == 0 and visited[y][x - 1] != 1:
            grassFire(y, x - 1, XYArray, append, img, imgInv,visited, queue)

        elif y > 0 and img[y - 1][x] == 0 and visited[y - 1][x] != 1:
            grassFire(y - 1, x, XYArray, append, img, imgInv, visited, queue)

        elif len(queue) != 0:
            append = False
            x, y = queue.pop()
            grassFire(y, x, XYArray, append, img, imgInv, visited, queue)

        else:
            xArray, yArray = zip(*XYArray)

            maxX = max(xArray)
            maxY = max(yArray)

            minX = min(xArray)
            minY = min(yArray)


            if maxY - minY > 15 and maxX - minX > 10:
                letter = img[minY:maxY,  minX:maxX]
                letterInv = imgInv[minY:maxY,  minX:maxX]
                letterArray.append(letter)
                if TM:
                    cv2.imwrite('letter.png', letter)
                    lt = cv2.imread('letter.png',0)
                    result = templateMatch(lt)
                    letters.append(result)
                elif KNN:
                    cv2.imwrite('letter.png', letterInv)
                    result = knnresult2()
                    letters.append(result)
                #plt.imshow(letter, cmap='gray')
                #plt.title("Letter")
                #plt.show()
    except:
        print('Grassfire error')

class ContourWithData():
    npaContour = None           # contour
    boundingRect = None         # bounding rect for contour
    intRectX = 0                # bounding rect top left corner x location
    intRectY = 0                # bounding rect top left corner y location
    intRectWidth = 0            # bounding rect width
    intRectHeight = 0           # bounding rect height
    fltArea = 0.0               # area of contour

    def calculateRectTopLeftPointAndWidthAndHeight(self):               # calculate bounding rect info
        [intX, intY, intWidth, intHeight] = self.boundingRect
        self.intRectX = intX
        self.intRectY = intY
        self.intRectWidth = intWidth
        self.intRectHeight = intHeight

    def checkIfContourIsValid(self):                            # this is oversimplified, for a production grade program
        if self.fltArea < MIN_CONTOUR_AREA: return False        # much better validity checking would be necessary
        return True

def knnresult2():

    try:
        npaClassifications = np.loadtxt("classifications.txt", np.float32)                  # read in training classifications
    except:
        print ("error, unable to open classifications.txt, exiting program\n")
        os.system("pause")
        return

    try:
        npaFlattenedImages = np.loadtxt("flattened_images.txt", np.float32)                 # read in training images
    except:
        print ("error, unable to open flattened_images.txt, exiting program\n")
        os.system("pause")
        return

    npaClassifications = npaClassifications.reshape((npaClassifications.size, 1))       # reshape numpy array to 1d, necessary to pass to call to train
    kNearest = cv2.ml.KNearest_create()                   # instantiate KNN object
    kNearest.train(npaFlattenedImages, cv2.ml.ROW_SAMPLE, npaClassifications)

    imgTestingNumbers = cv2.imread("letter.png",0)          # read in testing numbers image

    imgROIResized = cv2.resize(imgTestingNumbers, (RESIZED_IMAGE_WIDTH, RESIZED_IMAGE_HEIGHT))             # resize image, this will be more consistent for recognition and storage
    npaROIResized = imgROIResized.reshape((1, RESIZED_IMAGE_WIDTH * RESIZED_IMAGE_HEIGHT))      # flatten image into 1d numpy array
    npaROIResized = np.float32(npaROIResized)       # convert from 1d numpy array of ints to 1d numpy array of floats

    retval, npaResults, neigh_resp, dists = kNearest.findNearest(npaROIResized, k = 3)     # call KNN function find_nearest
    print(retval)
    print(neigh_resp)
    strCurrentChar = str(chr(int(npaResults[0][0])))                                             # get character from results

    return strCurrentChar

detectedObjects = []
def notInList(newObject, thresholdDist):
    for detectedObject in detectedObjects:
        if math.hypot(newObject[0]-detectedObject[0], newObject[1]-detectedObject[1]) < thresholdDist:
            return False
    return True

charArray = []
def templateMatch(imgIn):
    output = "?"

    resizedP = cv2.resize(imgIn, (35,45), interpolation=cv2.INTER_AREA)
    for i in range (0, len(charArray)):
        tem = charArray[i]
        cv2.imwrite('tem.png',tem)
        tem = cv2.imread('tem.png',0)
        tem = cv2.resize(tem, (35,45), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(resizedP, tem, cv2.TM_CCOEFF_NORMED)
        threshold = 0.6
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            print(i)
            if len(detectedObjects) == 0 or notInList(pt, 15):
                if i <=25:
                    output = chr(ord('A')+i)
                    return output
                else:
                    output = chr(ord('0')+(i-26))
                    return output
    return output

def createTemps(letters,numbers):
    for i in range (0,26):
        letter = letters[8:52,(i * 38)+3:(i * 38 + 38)-2]
        charArray.append(letter)
    for i in range(0,10):
        nums = numbers[5:51,(i * 38)+4:(i * 38 + 38)-5]
        charArray.append(nums)

lt = cv2.imread('letters.png',0)
num = cv2.imread('numbers.png',0)
images = []
#print(sys.getrecursionlimit())
sys.setrecursionlimit(2000)
def loadImages(folder):
    print('Loading data set')
    for file in os.listdir(folder):
        img = cv2.imread(os.path.join(folder, file))
        if img is not None:
            images.append(img)
    print('Completed')

loadImages(r'C:\Users\Ciprian\Documents\GitHub\p3_fuckup\OCR_Test\License_plates')
for img in images:
    letters = []
    grayImg = np.zeros((img.shape[0], img.shape[1]))
    binaryImg = np.zeros((img.shape[0], img.shape[1]))
    binaryImg2 = np.zeros((img.shape[0], img.shape[1]))
    grayScale(img)
    pl = cv2.imread('plate.jpg')
    cv2.imshow('Plate',pl)
    cv2.waitKey(0)