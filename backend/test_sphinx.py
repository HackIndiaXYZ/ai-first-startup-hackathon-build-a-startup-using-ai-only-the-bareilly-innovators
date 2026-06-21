from pocketsphinx import LiveSpeech
print("Listening for wake word...")
for phrase in LiveSpeech(keyphrase='hey sivi', kws_threshold=1e-20):
    print("Wake word detected!")
    break
