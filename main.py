import binascii
import datetime
import inspect
import math
import random
import python3_midi as midi
import numpy as np
import pandas as pd
from midi2audio import FluidSynth
import ccxt

eot = midi.EndOfTrackEvent(tick=1)
VOLUME = 200
DUR_SEQ = [2, 2, 1, 2, 2, 2, 1]
MOLL_SEQ = [2, 1, 2, 2, 1, 2, 2]


def parse_rates_data(pair, timeframe, start, limit):
    exchange = ccxt.binance()
    timestamp = int(datetime.datetime.strptime(start, "%Y-%m-%d %H:%M:%S%z").timestamp() * 1000)
    response = exchange.fetch_ohlcv(pair, timeframe, timestamp, limit)

    # [
    #     1516792860000, // timestamp
    #     11110,    // open
    #     11110.29, // high
    #     11050.91, // low
    #     11052.27, // close
    #     39.882601 // volume
    # ]

    transposed = np.array(response).transpose()
    data = np.array(transposed)
    return data


def project_data_to_range(data, min_pitch, max_pitch):
    maximum, minimum = np.max(data), np.min(data)
    step = (maximum - minimum) / (max_pitch - min_pitch)
    shift = minimum // step - min_pitch

    pitches = []
    for i in data:
        pitches.append(int(i / step - shift))
    return pitches


def data_to_pitches_in_scale(data, min_pitch, max_pitch, tonality):
    maximum, minimum = np.max(data), np.min(data)
    notes = get_scale(min_pitch, max_pitch, tonality)

    step = (maximum - minimum) / len(notes)
    shift = minimum // step

    pitches = []
    for i in data:
        el = min(int(i / step - shift), len(notes) - 1)
        pitches.append(notes[el])
    return pitches


def single_track(pitches):
    track = midi.Track()
    for i in range(len(pitches)):
        on_note = midi.NoteOnEvent(tick=0, channel=0, pitch=pitches[i], velocity=VOLUME)
        off_note = midi.NoteOffEvent(tick=120, channel=0, pitch=pitches[i])
        track.append(on_note)
        track.append(off_note)
    return track


def single_track_variable_volume(pitches, volume_data):
    track = midi.Track()
    for i in range(len(pitches)):
        on_note = midi.NoteOnEvent(tick=0, channel=0, pitch=pitches[i], velocity=volume_data[i])
        off_note = midi.NoteOffEvent(tick=120, channel=0, pitch=pitches[i])
        track.append(on_note)
        track.append(off_note)
    return track


def get_scale(start_pitch, end_pitch, tonality):
    result = []

    if start_pitch < 0 or start_pitch > end_pitch:
        return result

    if tonality == "DUR":
        seq = DUR_SEQ
    elif tonality == "MOLL":
        seq = MOLL_SEQ
    else:
        return result

    current_pitch = start_pitch
    result.append(current_pitch)

    for i in seq * 7:
        current_pitch += i
        if current_pitch > end_pitch:
            break
        result.append(current_pitch)

    return result


def test_sound():
    pattern = midi.Pattern()
    track = midi.Track()
    filename = 'output/test.mid'
    start, size = 60, 13
    pitches = get_scale(50, 107, "DUR")
    for i in pitches:
        pitch = i
        on_note = midi.NoteOnEvent(tick=0, channel=0, data=[pitch, VOLUME])
        off_note = midi.NoteOffEvent(tick=250, channel=0, data=[pitch, VOLUME])
        # on_note = midi.NoteOnEvent(tick=0, channel=0, pitch=pitch, velocity=VOLUME)
        # off_note = midi.NoteOffEvent(tick=250, channel=0, pitch=pitch)

        # pitch = int(min_pitch + data(math.pi * i / (float(min_pitch) / 5)) * pitch_range)
        # volume = random.randint(VOLUME, VOLUME + int(min_pitch / 8))
        # on_note = midi.NoteOnEvent(tick=0, channel=0, data=[pitch, volume])
        # off_note = midi.NoteOffEvent(tick=140, channel=0, data=[pitch, volume])

        track.append(on_note)
        track.append(off_note)

    pattern.append(track)
    midi.write_midifile(filename, pattern)
    fs = FluidSynth
    fs('fonts/GuitarA.sf2').play_midi(filename)


if __name__ == '__main__':
    # test_sound()

    # Parameters for making pattern
    filename, max_notes, tracks, min_pitch, pitch_range = "output/sin_triple.mid", 70, 1, 50, 30

    pair = 'BTC/USDT'
    timeframe = '1h'
    start = "2022-01-24 11:20:00+00:00"
    limit = 100
    data = parse_rates_data(pair, timeframe, start, limit)
    min_pitch, max_pitch = 31, 103
    pitches = data_to_pitches_in_scale(data[4], min_pitch, max_pitch, "DUR")
    # print(f"Minimum : {np.min(pitches)}")
    # print(f"Maximum : {np.max(pitches)}")

    # Write the MIDI
    # pattern = make_pattern(max_notes, len(data), min_pitch, pitch_range, data)
    # if pattern == -1:
    #     exit(-1)
    # midi.write_midifile(filename, pattern)

    min_velocity, max_velocity = 100, 255
    velocity_data = project_data_to_range(data[5], min_velocity, max_velocity)

    pattern = midi.Pattern()
    pattern.append(single_track_variable_volume(pitches, velocity_data))
    if pattern == -1:
        exit(-1)
    midi.write_midifile(filename, pattern)

    # Play the MIDI
    fs = FluidSynth
    fs('fonts/GuitarA.sf2').play_midi(filename)
