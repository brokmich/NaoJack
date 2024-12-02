#

import time

import cv2
import numpy as np

from naoqi import ALProxy

import random

suits = ['Clubs', 'Diamonds', 'Hearts', 'Spades']

suits_map = {
    'Clubs': 'Treboles',
    'Diamonds': 'Diamantes',
    'Hearts': 'Corazones',
    'Spades': 'Picas'
}

suggestion_map = {
    'Stand': 'Quedar',
    'Hit': 'Pedir'
}

ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

values = {
  '2':  2.0,
  '3':  3.0,
  '4':  4.0,
  '5':  5.0,
  '6':  6.0,
  '7':  7.0,
  '8':  8.0,
  '9':  9.0,
  '10': 10.0,
  'J':  10.0,
  'Q':  10.0,
  'K':  10.0,
  'A':  11.0
}

PLAY = 'jugar'
LOOK = 'ver'
ASSIST = 'ayudar'
STAND = 'quedar'
THANK_YOU = 'gracias'

deck_count = 8

global deck
global_deck = [(rank, suit) for rank in ranks for suit in suits] * deck_count

def get_hand_value(hand):
    hand_value = 0
    aces = 0

    for rank, _ in hand:
        hand_value += values[rank]

        if rank == 'A':
            aces += 1

    while hand_value > 21 and aces > 0:
        hand_value -= 10
        aces -= 1

    return hand_value

global hand
global_hand = []

def give_card(card):
    global_hand.append(card)
    global_deck.remove(card)

def get_bust_probability(sims = 1000):
    bust = 0.0
    
    for _ in range(sims):
        sim_hand = global_hand[:]
        
        while True:
            sim_card = random.choice(global_deck)
            sim_hand.append(sim_card)
            sim_value = get_hand_value(sim_hand)
            
            if sim_value > 21:
                bust += 1.0
                break
            elif sim_value >= 17:
                break
    
    return bust / sims

def get_hit_probability(sims = 1000):
    hit = 0.0
    
    for _ in range(sims):
        sim_hand = global_hand[:]
        
        while True:
            sim_card = random.choice(global_deck)
            sim_hand.append(sim_card)
            sim_value = get_hand_value(sim_hand)
            
            if sim_value == 21:
                hit += 1.0
                break
            elif sim_value >= 17:
                break
    
    return hit / sims

def get_suggestion():
    value = get_hand_value(global_hand)

    if value == 21:
        return 'Stand'

    if value >= 22:
        return 'Bust'

    if value <= 11:
        return 'Hit'

    bust_probability = get_bust_probability()
    hit_probability = get_hit_probability()

    print("Probabilidad de perder: {}".format(bust_probability))
    print("Probabilidad de ganar: {}".format(hit_probability))

    if bust_probability > 0.40:
        return 'Stand'
    
    # if hit_probability > 0.25:
    #     return 'Hit'

    return 'Hit'

def get_card_from_data(data):
    tuple = data.split(" ")
    rank = tuple[0]
    suit = tuple[1]
    return (rank, suit)

def main():
    # Replace with the actual IP address of your NAO robot
    robot_ip = "10.1.138.30" # Change to your NAO's IP address
    robot_port = 9559 # Default port for NAOqi

    # Create proxies for the ALTextToSpeech and ALSpeechRecognition services
    tts = ALProxy("ALTextToSpeech", robot_ip, robot_port)
    asr = ALProxy("ALSpeechRecognition", robot_ip, robot_port)
    video_proxy = ALProxy("ALVideoDevice", robot_ip, robot_port)
    memory = ALProxy("ALMemory", robot_ip, robot_port)

    # Set language for text to speech and speech recognition
    tts.setLanguage("Spanish")
    asr.setLanguage("Spanish")
    
    # Start speech recognition
    vocabulary = [PLAY, LOOK, ASSIST, THANK_YOU, STAND]
    asr.setVocabulary(vocabulary, True)

    # Subscribe to the camera
    resolution = 2 # 640x480
    color_space = 11 # RGB
    fps = 30
    camera_name = video_proxy.subscribeCamera("Camera", 0, resolution, color_space, fps)

    # QR code detector
    qr_detector = cv2.QRCodeDetector()

    # Start the speech recognition service
    asr.subscribe("NaoJack")

    tts.say("Hola, vamos a jugar!")

    try:
        start(tts, video_proxy, camera_name, qr_detector, memory)

    except KeyboardInterrupt:
        print("Program interrupted by user.")

    finally:
        asr.unsubscribe("NaoJack")
        video_proxy.unsubscribe(camera_name)
        cv2.destroyAllWindows()

def start(tts, video_proxy, camera_name, qr_detector, memory):
    while True:
        # Wait for the user to say something
        time.sleep(1) # Adjust time as needed

        result = memory.getData("WordRecognized")

        if result and len(result) > 0 and len(result[0]) > 0:
            recognized_text = result[0][6:-6]
            confidence = result[1]
            
            if confidence > 0.51:
                print("Confianza: ".format(confidence))

                tts.say("Dijiste {}?".format(recognized_text))
                
                confirmation = raw_input("Dijiste: {}? ".format(recognized_text))
                
                if confirmation == "y":
                    # Respond based on the recognized text
                    if recognized_text == PLAY:
                        tts.say("Hola estoy listo para ayudar")
                        print("Hola estoy listo para ayudar")

                    elif recognized_text == LOOK:
                        time.sleep(2)
                        tts.say("Estoy escaneando")
                        print("Estoy escaneando")
                        # Get a camera image
                        nao_image = video_proxy.getImageRemote(camera_name)

                        if nao_image is None:
                            print("No puede leer la carta")
                            tts.say("No puede leer la carta")
                            continue

                        # Convert the image to a format OpenCV can use
                        width = nao_image[0]
                        height = nao_image[1]

                        array = np.frombuffer(nao_image[6], dtype=np.uint8)
                        image = array.reshape((height, width, 3))

                        # Convert BGR to RGB
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                        # Detect QR codes
                        # data, _ = qr_detector(image)
                        data, _, _ = qr_detector.detectAndDecode(image)

                        if data:
                            card = get_card_from_data(data)
                            tts.say("La carta es: {} de {}.".format(card[0], suits_map[card[1]]))
                            print("La carta es: {} de {}.".format(card[0], suits_map[card[1]]))
                            give_card(card)
                        else:
                            tts.say("No encontre un codigo")
                            print("No encontre un codigo")

                    elif recognized_text == ASSIST:
                        tts.say("Estoy pensando")
                        print("Estoy pensando")
                        value = get_hand_value(global_hand)
                        
                        tts.say("Tu puntaje es {}.".format(value))
                        print("Tu puntaje es {}.".format(value))

                        suggestion = get_suggestion()

                        if suggestion == 'Bust':
                            tts.say("Lo siento has perdido")
                            global_hand[:] = []
                        else:
                            tts.say("Mi sugerencia es que tienes que {}.".format(suggestion_map[suggestion]))

                    elif recognized_text == STAND:
                        global_hand[:] = []
                        tts.say("Elegiste quedar. Buena suerte!")
                        print("Elegiste quedar. Buena suerte!")

                    elif recognized_text == THANK_YOU:
                        tts.say("Adios, ten un buen dia")
                        print("Adios, ten un buen dia")
                        break

if __name__ == "__main__":
    main()
