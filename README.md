# Server providing AI features for RPGs

This is an experimental solution of integrating LLMs into the good old Morrowind.

What it does in short:
- player can speak with microphone, voice gets recognized (STT = speech-to-text)
- NPC can generate response using power of a chosen LLM
- and finally NPC speaks the generated line (TTS = text-to-speech)

Be aware that description below requires a bit of a technical knowledge from the reader.

# Basics

Currently, mod supports only vanilla Morrowind MWSE (not OpenMW).

How to set it up:

- copy `mwse_mod` directory into `Data Files\MWSE`, or use mod organizer
- prepare `config.yml`
- run server

```sh
D:\Python\Python312\python.exe .\src\server\main.py --config .\config.yml
```

- if everything is alright, server will say

```
<...>
Waiting for the Morrowind to connect to the server...
```

- now it is time for the game to connect to the server. Launch the Morrowind if not yet, or wait as by default mod tries to reconnect every 10 sec

- after it is connected, server will tell you this

```
Client #::1:29227 connected
```

and you will also see a notification in the game

- server will speak to the game and get the initial context. Eventually, you should see something

```
INFO [SUCCESS] Game master started in 6.078705072402954 sec
INFO Happy playing, game master is ready
```

- now you should be good to go: speak to NPC and see the result.

# Setting it up

You have to prepare config file. Use `config.yml.example` as a starting point. Or generate new config using `--write-default-config` command line argument.

Config is big enough. Visit `src\server\app\app_config.py` to check out it in details.

## LLM

Currently supported LLM: Google, Mistral, any OpenAI-compatible, Claude.

I personally find Google Gemini (`gemini-1.5-flash` or `gemini-2.0-flash`) the easiest to use. Here's how to set it up:

- go to Google Cloud Console, create project, select Gemini API, create credentials for it, copy the API key, paste it in the config:

```yaml
llm:
  system:
    type: google

    google:
      api_key: ENTER_HERE
      # model_name: gemini-1.5-flash
      model_name: gemini-2.0-flash
  llm_logger:
    directory: D:\Games\immersive_morrowind_llm_logs
    max_files: 300
```

## Minimal setup

The most bare minimum setup is to have only LLM without STT and TTS - so you would need to chat with NPC only. To set it up, `speech_to_text` and `text_to_speech` in the config set to `dummy` system.


## STT

Currently, server supports only Vosk and Microsoft Speech.

Download Vosk models from here: https://alphacephei.com/vosk/models. For Russian, `vosk-model-small-ru-0.22` works good enough.

For Microsoft Speech, you would need to set up project in Azure Portal https://portal.azure.com, create Speech API key, and paste it in the config.

## TTS

Currently supports only Elevenlabs as in my personal opinion, it is the only service which produces non-robotic speeches, and sounds good. But it should be easy enough to integrate other services.

The setup here is a bit more complex.

1. Get API key and add it to the config.

2. You need to create voices for each pair `(race, gender)`, plus there is a separate voice for `Socucius` as in Russian localization the NPC is voiced by the gloricus voice actor Rogvold Suhoverko.

Create file `morrowind-voices-concat.sh` (the syntax is for Git Bash; for Powershell it should be rewritten):

```sh
#!/bin/bash -x

# RACE="bm"
rm /d/voices-${RACE}.txt;
for f in *.mp3; do echo "file '${PWD}/$f'" | sed 's/\/c\//C:\//'; done > /d/voices-${RACE}.txt;
/d/ffmpeg/bin/ffmpeg.exe -f concat -safe 0 -i /d/voices-${RACE}.txt -c copy /d/concat-${RACE}-full.mp3
/d/ffmpeg/bin/ffmpeg.exe -ss 0 -t 300 -i /d/concat-${RACE}-full.mp3 -c:a copy /d/concat-${RACE}-trimmed.mp3
```

3. Now, you need to create voices for each race and gender. Go to `Data Files\Sound\Vo`, and, say for dunmer male: `Data Files\Sound\Vo\d\m`, and run the command:

```sh
RACE=dm /d/dev/morrowind-voices-concat.sh
```

This will generate two files: `/d/concat-dm-full.mp3` and `/d/concat-dm-trimmed.mp3`. Last one is good for using in Elevenlabs: upload it in there.

4. After that, you would need to copy voice ID of the newly created voice, and set it in the config:

```yaml
text_to_speech:
  system:
    type: elevenlabs
    elevenlabs:
      api_key: ENTER_HERE
      language_code: ru
      model_id: eleven_flash_v2_5
      max_wait_time_sec: 10

      voices:
        d_male: ENTER_HERE
```

5. Do this for every single race and gender. After all voices are uploaded, NPC should be able to speak.

### ffmpeg

FFmpeg is optional. It can be used to adjust pitch of the file, and speed it up a bit to avoid too long speeches.

## Database

Database is where server stores all the known context for all used NPCs. Specify the wanted directory to store data in:

```yaml
database:
  directory: D:\Games\immersive_morrowind_db
```

Stored data is 100% readable by a human. Check it out and play with it, tweak some personalities, etc.

Database is read upon starting the server. If you change something in the DB, restart the server.
Restarting server during gameplay is OK.

# FAQ

Q: Can it be integrated with other games?
A: In theory - yes. One would need to implement "game mod", and adjust "server side" accordingly.

# Some technical details

Server is written in the way that integration of another LLM/STT/TTS system should be as transparent as possible.

# Authors

Dmitry Zganyaiko https://linkedin.com/in/zdooo
