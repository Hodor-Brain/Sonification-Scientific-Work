import binascii
import datetime
import inspect
import math
import random
import python3_midi as midi
import numpy as np
import pandas as pd
from midi2audio import FluidSynth

eot = midi.EndOfTrackEvent(tick=1)
VOLUME = 200


def parse_excel_data(data):
    data = pd.read_excel(data[0], sheet_name=data[1])
    data = data.values.transpose()

    lst = data.tolist()

    for i in range(len(lst)):
        for j in range(len(lst[i])):
            if not isinstance(lst[i][j], str):
                lst[i][j] = str(lst[i][j])
            lst[i][j] = str(int((binascii.hexlify(lst[i][j].encode('utf-8'))).decode('utf-8'), 16))

    data = np.array(lst)

    return data, len(data)


def make_single_track(notes_limit, min_pitch, pitch_range, data=None):
    track = midi.Track()

    if data is not None:
        if inspect.isfunction(data):
            track = track_function(notes_limit, min_pitch, pitch_range, track, data)
        if type(data) is np.ndarray:
            if len(data.shape) == 1:
                track = track_excel(notes_limit, min_pitch, pitch_range, track, data)
            if len(data.shape) == 2:
                track = track_img(notes_limit, min_pitch, pitch_range, track, data)
    else:
        track = track_random(notes_limit, min_pitch, pitch_range, track)

    track.append(eot)
    return track


def track_function(notes_limit, min_pitch, pitch_range, track, data):
    for i in range(notes_limit):
        pitch = int(min_pitch + data(math.pi * i / (float(min_pitch) / 5)) * pitch_range)
        volume = random.randint(VOLUME, VOLUME + int(min_pitch / 8))
        on_note = midi.NoteOnEvent(tick=0, channel=0, data=[pitch, volume])
        off_note = midi.NoteOffEvent(tick=140, channel=0, data=[pitch, volume])

        track.append(on_note)
        track.append(off_note)

    return track


def track_img(notes_limit, min_pitch, pitch_range, track, data):
    per_note = int(len(data) / notes_limit)

    for i in range(notes_limit):
        shift = i * per_note
        denominator = per_note * 255 * 3
        numerator = 0
        for j in range(per_note):
            numerator += int(data[j + shift][0]) + int(data[j + shift][1]) + int(data[j + shift][2])

        normalized_pitch = numerator / denominator

        pitch = int(min_pitch + normalized_pitch * pitch_range)
        # volume = random.randint(55, 60 + int(min_pitch / 8))
        volume = VOLUME
        on_note = midi.NoteOnEvent(tick=0, channel=0, data=[pitch, volume])
        off_note = midi.NoteOffEvent(tick=140, channel=0, data=[pitch, volume])

        track.append(on_note)
        track.append(off_note)

    return track


def track_excel(notes_limit, min_pitch, pitch_range, track, data):
    per_note = int(len(data) / notes_limit)

    for i in range(notes_limit):
        shift = i * per_note
        numerator = sum(int(data[j + shift]) for j in range(per_note))
        # for j in range(per_note):
        #     numerator += int(data[j + shift])
        denominator = 10 ** (len(str(numerator)))

        normalized_pitch = numerator / denominator

        pitch = int(min_pitch + normalized_pitch * pitch_range)
        # volume = random.randint(55, 60 + int(min_pitch / 8))
        volume = VOLUME
        on_note = midi.NoteOnEvent(tick=0, channel=0, data=[pitch, volume])
        off_note = midi.NoteOffEvent(tick=140, channel=0, data=[pitch, volume])

        track.append(on_note)
        track.append(off_note)

    return track


def track_random(notes_limit, min_pitch, pitch_range, track):
    for i in range(notes_limit):
        pitch = random.randint(min_pitch, min_pitch + pitch_range)
        on_note = midi.NoteOnEvent(tick=0, channel=0, data=[pitch, 75])
        off_note = midi.NoteOffEvent(tick=140, channel=0, data=[pitch, 75])
        track.append(on_note)
        track.append(off_note)

    return track


def make_pattern(limit, number_of_tracks, min_pitch, pitch_range, data=None):
    pattern = midi.Pattern()
    n = number_of_tracks

    if n >= 1:
        track_range = pitch_range / n
        for i in range(n - 1):
            track = make_single_track(limit, min_pitch + i * track_range, track_range, data[i])
            pattern.append(track)

        track = make_single_track(limit, min_pitch + (n - 1) * track_range, pitch_range - (n - 1) * track_range,
                                  data[n - 1])
        pattern.append(track)
    else:
        print("Error: number of tracks must be integer bigger than 0")
        return -1

    return pattern


def parse_rates_data(pair, timeframe, start, limit):
    import ccxt

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


def data_to_pitches(data, min_pitch, max_pitch):
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


DUR_SEQ = [2, 2, 1, 2, 2, 2, 1]
MOLL_SEQ = [2, 1, 2, 2, 1, 2, 2]


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
    timeframe = '6h'
    start = "2023-01-24 11:20:00+00:00"
    limit = 100
    data = parse_rates_data(pair, timeframe, start, limit)
    pitches = data_to_pitches_in_scale(data[4], 24, 108, "MOLL")
    # print(f"Minimum : {np.min(pitches)}")
    # print(f"Maximum : {np.max(pitches)}")

    # Write the MIDI
    # pattern = make_pattern(max_notes, len(data), min_pitch, pitch_range, data)
    # if pattern == -1:
    #     exit(-1)
    # midi.write_midifile(filename, pattern)

    pattern = midi.Pattern()
    pattern.append(single_track(pitches))
    if pattern == -1:
        exit(-1)
    midi.write_midifile(filename, pattern)

    # Play the MIDI
    fs = FluidSynth
    fs('fonts/HL1_Crowbar_Soundfont.sf2').play_midi(filename)
