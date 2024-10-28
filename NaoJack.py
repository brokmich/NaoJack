#

import time

import cv2
import numpy as np
from naoqi import ALProxy

suits = ['Clubs', 'Diamonds', 'Hearts', 'Spades']

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

deck_count = 1

deck = [(rank, suit) for rank in ranks for suit in suits] * deck_count

global hand
hand = []

def give_card(card):
    hand.append(card)
    deck.remove(card)

def get_hand_value():
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

def get_suggestion():
    value = get_hand_value()

    if value == 21:
        return 'Stand'

    if value >= 22:
        return 'Bust'

    if value <= 11:
        return 'Hit'

    suggestion = 'Stand'

    counts = { rank: 0 for rank in ranks }

    chances = { rank: deck_count * 4.0 for rank in ranks }

    for rank, _ in deck:
        counts[rank] += 1

    for rank in ranks:
        chances[rank] = 4.0 * deck_count - counts[rank]

    if get_low_card_chance(chances) > get_high_card_chance(chances):
        suggestion = 'Hit'

    return suggestion

def get_low_card_chance(chances):
    low_cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9']

    return sum([chances[rank] for rank in low_cards])

def get_high_card_chance(chances):
    high_cards = ['10', 'J', 'Q', 'K']

    return sum([chances[rank] for rank in high_cards])

def get_card_from_data(data):
    tuple = data.split(" ")
    rank = tuple[0]
    suit = tuple[1]
    return (rank, suit)

# # create python module
# class MyModule(ALModule):
#   """ Mandatory docstring.
#       comment needed to create a new python module
#   """

#   def myCallback(self, key, value, message):
#     """ Mandatory docstring.
#         comment needed to create a bound method
#     """
#     print(key, value, message)

def main():
    # Replace with the actual IP address of your NAO robot
    robot_ip = "10.1.138.114" # Change to your NAO's IP address
    robot_port = 9559 # Default port for NAOqi

    # Create proxies for the ALTextToSpeech and ALSpeechRecognition services
    tts = ALProxy("ALTextToSpeech", robot_ip, robot_port)
    asr = ALProxy("ALSpeechRecognition", robot_ip, robot_port)
    video_proxy = ALProxy("ALVideoDevice", robot_ip, robot_port)
    memory = ALProxy("ALMemory", robot_ip, robot_port)

    # Set language for text to speech and speech recognition
    tts.setLanguage("English")
    asr.setLanguage("English")
    
    # Start speech recognition
    vocabulary = ["Play", "Look", "Assist me", "Thank you", "Stand"]
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
    tts.say("Now Listening!")

    try:
        start(asr, tts, video_proxy, camera_name, qr_detector, memory)

    except KeyboardInterrupt:
        print("Program interrupted by user.")

    finally:
        asr.unsubscribe("NaoJack")
        video_proxy.unsubscribe(camera_name)
        cv2.destroyAllWindows()

def start(asr, tts, video_proxy, camera_name, qr_detector, memory):
    past_word = ""
    while True:
        # Wait for the user to say something
        time.sleep(1) # Adjust time as needed

        result = memory.getData("WordRecognized")
        if result and len(result) > 0 and len(result[0]) > 0:
            recognized_text = result[0][6:-6]
            
            if past_word != recognized_text:
                print("You said: {}.".format(recognized_text))
                past_word = recognized_text
                
                # Respond based on the recognized text
                if recognized_text == "Play":
                    print("Now playing")
                    tts.say("Hey! I am ready to assist you.")

                elif recognized_text == "Look":
                    time.sleep(2)
                    print("Now looking")
                    tts.say("Starting scan.")
                    # Get a camera image
                    nao_image = video_proxy.getImageRemote(camera_name)

                    if nao_image is None:
                        print("Could not get image from camera.")
                        continue

                    # Convert the image to a format OpenCV can use
                    width = nao_image[0]
                    height = nao_image[1]
                    print(width, height)

                    array = np.frombuffer(nao_image[6], dtype=np.uint8)
                    image = array.reshape((height, width, 3))

                    # Convert BGR to RGB
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                    # Detect QR codes
                    # data, _ = qr_detector(image)
                    data, boundingbox, rectimage = qr_detector.detectAndDecode(image)
                    print(data, boundingbox, rectimage)

                    if data:
                        print("QR Code detected: {}".format(data))
                        tts.say("I found a QR code with data: {}".format(data))
                        card = get_card_from_data(data)
                        tts.say("The card is: {} of {}.".format(card[0], card[1]))
                        give_card(card)
                    else:
                        tts.say("No QR code found.")

                elif recognized_text == "Assist me":
                    print("Now suggesting")
                    suggestion = get_suggestion()

                    if suggestion == 'Bust':
                        tts.say("I'm sorry, you have lost.")
                        hand[:] = []
                    else:
                        tts.say("This is my suggestion. You should {}.".format(suggestion))

                elif recognized_text == "Stand":
                    hand[:] = []
                    tts.say("You chose to stand. Good luck!")

                elif recognized_text == "Thank you":
                    print("Now good bye")
                    tts.say("Goodbye! Have a great day!")
                    break

def test():
    print(deck)

    hand.append(deck.pop())
    print(hand)
    print(get_hand_value())
    print(get_suggestion())

    hand.append(deck.pop())
    print(hand)
    print(get_hand_value())
    print(get_suggestion())

    hand.append(deck.pop())
    print(hand)
    print(get_hand_value())
    print(get_suggestion())

if __name__ == "__main__":
    main()
