#!/bin/bash
# Shell script to replace TTS in snips with AWS polly
#
# Install and configure aws cli as per https://docs.aws.amazon.com/polly/latest/dg/getting-started-cli.html
# Installed in /home/<user>/.local/bin, configure with aws configure and provide key, secret, etc.
#
# in /etc/snips.toml, change TTS config to contain following 3 lines
# [snips-tts]
# provider = "customtts"
# customtts = { command = ["/usr/local/bin/custom_tts.sh", "-w", "%%OUTPUT_FILE%%", "-l", "%%LANG%%", "%%TEXT%%"] }
#
# install mpg123 (apt-get install mpg123) for the mp3->wav conversion
#
# This will run e.g. '"/usr/local/bin/custom_tts.sh" "-w" "/tmp/.tmpbQHj3W.wav" "-l" "en" "For how long?"'
# 
# Input text and parameters will be used to calculate a hash for caching the mp3 files so only
# "new speech" will call polly, existing mp3s will be transformed in wav files directly

export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_DEFAULT_REGION="eu-west-3"

# Path to aws binary
awscli='/home/pi/.local/bin/aws'

# Get hotword
hotword=$(head -n 1 '/home/pi/snips/hotword.txt')

# Voice to use

if [ "$hotword" == "paprika" ]; then
    voice="Celine"
    # Folder to cache the files - this also contains the .txt file with all generated mp3
    cache='/home/pi/snips-tts-cache-paprika/'
fi
if [ "$hotword" == "marin" ]; then
    voice="Mathieu"
    # Folder to cache the files - this also contains the .txt file with all generated mp3
    cache='/home/pi/snips-tts-cache-marin/'
fi
echo 'Voice: ' $voice
echo 'cache folder: ' $cache

# Should not need to change parameters below this
# format to use
format="mp3"

# Sample rate to use
samplerate="22050"

lang="$4"
echo 'Lang: ' $lang

# passed text string
text="<speak><lang xml:lang=\"$lang\">$5</lang></speak>"
echo 'Input text:' $text

# target file to return to snips-tts (wav)
outfile="$2"
echo 'Output file:' $outfile 

# check/create cache if needed
mkdir -pv "$cache"

# hash for the string based on params and text
md5string="$text""_""$voice""_""$format""_""$samplerate"
echo 'Using string for hash': $md5string

hash="$(echo -n "$md5string" | md5sum | sed 's/ .*$//')"
echo 'Calculated hash:' $hash

cachefile="$cache""$hash".mp3
echo 'Cache file:' $cachefile 

# do we have this?
if [ -f "$cachefile" ]
then
    echo "$cachefile found."
    # convert
    mpg123 -w "$outfile" "$cachefile"
else
    echo "$cachefile not found, running polly"
    # execute polly to get mp3 - check paths, voice set to Salli
    $awscli polly synthesize-speech --output-format "$format" --voice-id "$voice" \
        --sample-rate "$samplerate" --text-type ssml --text "$text" "$cachefile"
    # update index
    echo "$hash" "$md5string" >> "$cache"index.txt
    # execute conversion to wav
    mpg123 -w $outfile $cachefile
fi

