#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import os
import argparse
import numpy as np
import shlex
import subprocess
import sys
import wave
from deepspeech import Model, printVersions
from timeit import default_timer as timer

try:
    from shhlex import quote
except ImportError:
    from pipes import quote


def list_files_in_directory(mypath):
    return [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]


# These constants control the beam search decoder

# Beam width used in the CTC decoder when building candidate transcriptions
BEAM_WIDTH = 500

# The alpha hyperparameter of the CTC decoder. Language Model weight
LM_ALPHA = 0.75

# The beta hyperparameter of the CTC decoder. Word insertion bonus.
LM_BETA = 1.85


# These constants are tied to the shape of the graph used (changing them changes
# the geometry of the first layer), so make sure you use the same constants that
# were used during training

# Number of MFCC features to use
N_FEATURES = 26

# Size of the context window used for producing timesteps in the input vector
N_CONTEXT = 9

def convert_samplerate(audio_path):
    sox_cmd = 'sox {} --type raw --bits 16 --channels 1 --rate 16000 --encoding signed-integer --endian little --compression 0.0 --no-dither - '.format(quote(audio_path))
    try:
        output = subprocess.check_output(shlex.split(sox_cmd), stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('SoX returned non-zero status: {}'.format(e.stderr))
    except OSError as e:
        raise OSError(e.errno, 'SoX not found, use 16kHz files or install it: {}'.format(e.strerror))

    return 16000, np.frombuffer(output, np.int16)


class VersionAction(argparse.Action):
    def __init__(self, *args, **kwargs):
        super(VersionAction, self).__init__(nargs=0, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        printVersions()
        exit(0)

def main():
    # parser = argparse.ArgumentParser(description='Running DeepSpeech inference.')
    # parser.add_argument('--model', required=True,
    #                     help='Path to the model (protocol buffer binary file)')
    # parser.add_argument('--alphabet', required=True,
    #                     help='Path to the configuration file specifying the alphabet used by the network')
    # parser.add_argument('--lm', nargs='?',
    #                     help='Path to the language model binary file')
    # parser.add_argument('--trie', nargs='?',
    #                     help='Path to the language model trie file created with native_client/generate_trie')
    # parser.add_argument('--audio', required=True,
    #                     help='Path to the audio file to run (WAV format)')
    # parser.add_argument('--version', action=VersionAction,
    #                     help='Print version and exits')
    # args = parser.parse_args()

    model = 'models/output_graph.pbmm'
    alphabet = 'models/alphabet.txt'
    lm = 'models/lm.binary'
    trie = 'models/trie'
    
    # savefolder = '/Users/shibozhang/Documents/Course/DeepLearningTopics_496/dataset/Edinburgh/clean_transcripts'
    # audiofolder = '/Users/shibozhang/Documents/Course/DeepLearningTopics_496/dataset/Edinburgh/clean_testset_wav/'

    savefolder = '/Users/shibozhang/Documents/Course/DeepLearningTopics_496/dataset/LibriSpeech_dataset/clean_transcripts'
    audiofolder = '/Users/shibozhang/Documents/Course/DeepLearningTopics_496/dataset/LibriSpeech_dataset/test_clean/wav/'

    if not os.path.exists(savefolder):
        os.mkdir(savefolder)
    
    audio_list = [os.path.join(audiofolder, i) for i in list_files_in_directory(audiofolder)]
    savefiles = [os.path.join(savefolder, i[:-4]+'.txt') for i in list_files_in_directory(audiofolder)]


    print('Loading model from file {}'.format(model), file=sys.stderr)
    model_load_start = timer()
    ds = Model(model, N_FEATURES, N_CONTEXT, alphabet, BEAM_WIDTH)
    model_load_end = timer() - model_load_start
    print('Loaded model in {:.3}s.'.format(model_load_end), file=sys.stderr)

    if lm and trie:
        print('Loading language model from files {} {}'.format(lm, trie), file=sys.stderr)
        lm_load_start = timer()
        ds.enableDecoderWithLM(alphabet, lm, trie, LM_ALPHA, LM_BETA)
        lm_load_end = timer() - lm_load_start
        print('Loaded language model in {:.3}s.'.format(lm_load_end), file=sys.stderr)

    for audio, savefile in zip(audio_list, savefiles):
        fin = wave.open(audio, 'rb')
        fs = fin.getframerate()
        if fs != 16000:
            print('Warning: original sample rate ({}) is different than 16kHz. Resampling might produce erratic speech recognition.'.format(fs), file=sys.stderr)
            fs, audio = convert_samplerate(audio)
        else:
            audio = np.frombuffer(fin.readframes(fin.getnframes()), np.int16)
        audio_length = fin.getnframes() * (1/16000)
        fin.close()
        print('Running inference.', file=sys.stderr)
        inference_start = timer()
        transcription = ds.stt(audio, fs)
        print(transcription)
        textfile = open(savefile, 'w')
        textfile.write(transcription)
        textfile.close()

        inference_end = timer() - inference_start
        print('Inference took %0.3fs for %0.3fs audio file.' % (inference_end, audio_length), file=sys.stderr)

if __name__ == '__main__':
    main()
