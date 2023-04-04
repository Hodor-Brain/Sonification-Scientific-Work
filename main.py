import datetime
import time
import midi2audio
import python3_midi as midi
import numpy as np
from midi2audio import FluidSynth
import ccxt
# import fluidsynth
from mingus.midi import fluidsynth as a
from mingus.midi import midi_track
from mingus.containers import note_container, note
import matplotlib.pyplot as plt
from matplotlib import animation
import random
import moviepy.editor as mpe

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


def single_track_variable_volume(pitches, volume_data, channel, tick):
    track = midi.Track()
    for i in range(len(pitches)):
        on_note = midi.NoteOnEvent(tick=0, channel=channel, pitch=pitches[i], velocity=volume_data[i])
        off_note = midi.NoteOffEvent(tick=tick, channel=channel, pitch=pitches[i])
        track.append(on_note)
        track.append(off_note)
    return track


def single_track_variable_volume_alt(pitches, volume_data):
    container = note_container.NoteContainer()
    for i in range(len(pitches)):
        container.add_note(note=note.Note().from_int(pitches[i]-12))
    return container


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


def visualize_data(pitches_list, labels, colors, interval, filename):
    track_number = len(pitches_list)
    if track_number == 0:
        return

    x = np.arange(len(pitches_list[0]))
    y = pitches_list

    fig, ax = plt.subplots()
    plt.xlabel("Index")
    plt.ylabel("Pitches")
    plt.title("Visualization")

    ax.axis([0, len(x), min_pitch, max_pitch])

    lines = [ax.plot(x, y[i], color=colors[i], label=labels[i])[0] for i in range(track_number)]

    def update(num, x, y, lines):
        for i in range(len(lines)):
            lines[i].set_data(x[:num], y[i][:num])
        return lines

    plt.legend(loc='upper left')
    ani = animation.FuncAnimation(fig, update, len(x), fargs=[x, y, lines], interval=interval)
    fps = 1000 / interval
    writer = animation.writers['ffmpeg'](fps=4, metadata=dict(artist="Me"), bitrate=-1)
    ani.save(filename, writer=writer)
    plt.show()


def get_data(pairs, timeframe, start, limit):
    return [parse_rates_data(pairs[i], timeframe, start, limit) for i in range(len(pairs))]


def get_pattern(data, min_pitch, max_pitch, tonality, min_velocity, max_velocity, tick):
    data_len = len(data)
    pitches_list = [data_to_pitches_in_scale(data[i][4], min_pitch, max_pitch, tonality) for i in range(data_len)]
    velocity_data= [project_data_to_range(data[i][5], min_velocity, max_velocity) for i in range(data_len)]

    pattern = midi.Pattern(single_track_variable_volume(pitches_list[i], velocity_data[i], 1, tick) for i in range(data_len))
    return pattern, pitches_list


if __name__ == '__main__':
    # test_sound()

    # Parameters for making pattern
    # filename, max_notes, tracks, min_pitch, pitch_range = "output/result.mid", 70, 1, 50, 30
    filename = "output/result.mid"

    timeframe = '1h'
    start = "2022-01-24 11:20:00+00:00"
    limit = 50
    pairs = [
        'BTC/USDT',
        # 'ETH/USDT',
        # 'SOL/USDT',
    ]
    data = get_data(pairs, timeframe, start, limit)

    min_pitch, max_pitch = 31, 103
    min_velocity, max_velocity = 50, 127
    tonality = "DUR"
    tick = 100
    pattern, pitches_list = get_pattern(data, min_pitch, max_pitch, tonality, min_velocity, max_velocity, tick)

    # Write the MIDI
    if pattern == -1:
        exit(-1)
    midi.write_midifile(filename, pattern)

    r = lambda: random.randint(0,255)
    colors = [f'#{r():02x}{r():02x}{r():02x}' for i in range(len(pairs))]
    # colors = ['red','green','blue', 'orange', 'blueviolet', 'magenta', 'lime']

    output_video_file = 'output/test.mp4'
    visualize_data(pitches_list, pairs, colors, tick, output_video_file)

    my_clip = mpe.VideoFileClip(output_video_file)

    output_audio_file = 'output/test.mp3'
    midi2audio.FluidSynth('fonts/FluidR3_GM.sf2').midi_to_audio(filename, output_audio_file)

    audio = mpe.AudioFileClip(output_audio_file)
    video1 = mpe.VideoFileClip(output_video_file)

    final = video1.set_audio(audio)
    final.write_videofile(output_video_file,codec= 'mpeg4' ,audio_codec='libvorbis')

    # plt.plot(np.arange(len(pitches_1)), pitches_1, color='r', label=pair_1)
    # plt.plot(np.arange(len(pitches_2)), pitches_2, color='g', label=pair_2)
    # plt.plot(np.arange(len(pitches_3)), pitches_3, color='b', label=pair_3)
    # plt.xlabel("Index")
    # plt.ylabel("Pitches")
    # plt.title("Visualization")
    # plt.legend()
    # plt.show()

    # Play the MIDI
    # fs = FluidSynth
    # fs('fonts/FluidR3_GM.sf2').play_midi(filename)

    # fs = fluidsynth.Synth()
    # fluidsynth.Synth().
    # fs.start()
    #
    # sfid = fs.sfload('fonts/FluidR3_GM.sf2')
    # fs.program_select(0, sfid, 0, 0)
    #
    # fs.noteon(0, 60, 30)
    # fs.noteon(0, 67, 30)
    # fs.noteon(0, 76, 30)
    #
    # time.sleep(1.0)
    #
    # fs.noteoff(0, 60)
    # fs.noteoff(0, 67)
    # fs.noteoff(0, 76)
    #
    # time.sleep(1.0)
    #
    # fs.delete()

    # a.init('fonts/FluidR3_GM.sf2',"dsound")
    # a.set_instrument(0, 34)
    # a.set_instrument(1, 35)
    #
    # note_container = single_track_variable_volume_alt(pitches_1, velocity_data_1)
    # track = midi_track.MidiTrack()
    # track.play_NoteContainer(note_container)
    # a.play_Track(track)
    #
    # a.play_Note(26, 0, 255)
    # a.sleep(0.5)
    # a.play_Note(26, 1, 255)
    # a.sleep(0.5)
