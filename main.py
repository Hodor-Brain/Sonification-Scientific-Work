import datetime
import sys

import python3_midi as midi
import numpy as np
from midi2audio import FluidSynth
import ccxt
import sf2_loader as sf
import matplotlib.pyplot as plt
from matplotlib import animation
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


def project_data_to_range(data, start, end):
    maximum, minimum = np.max(data), np.min(data)
    step = (maximum - minimum) / (end - start)
    shift = minimum // step - start

    pitches = []
    for i in data:
        pitches.append(int(i / step - shift))
    return pitches


def data_to_pitches_in_scale(data, min_pitch, max_pitch, mode):
    maximum, minimum = np.max(data), np.min(data)
    notes = get_scale(min_pitch, max_pitch, mode)

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


def get_scale(start_pitch, end_pitch, mode):
    result = []

    if start_pitch < 0 or start_pitch > end_pitch:
        return result

    if mode == "DUR":
        seq = DUR_SEQ
    elif mode == "MOLL":
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


def animate(fig, axs, x, y, lines, areas, interval):
    def update(num, x, y, lines, new_volumes):
        for i in range(len(lines)):
            lines[i].set_data(x[:num + 1], y[i][:num + 1])
            axs[i].scatter(x[num], y[i][num], s=new_volumes[i][num], c=colors[i])
        return lines

    return animation.FuncAnimation(fig, update, frames=len(x), fargs=[x, y, lines, areas], interval=interval)


def write_video(ani, interval, filename):
    fps = 1000 / (interval * 5)
    writer = animation.writers['ffmpeg'](fps=fps)
    ani.save(filename, writer=writer)


def visualize_pitches(pitches_list, volumes_list, labels, colors, interval, filename):
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

    lines = [ax.plot([], [], color=colors[i], label=labels[i])[0] for i in range(track_number)]
    new_volumes = [project_data_to_range(volumes_list[i], 2, 20) for i in range(track_number)]
    for i in range(track_number):
        ax.scatter(x[0], y[i][0], s=new_volumes[i][0], c=colors[i])
    plt.legend(loc='upper left')

    ani = animate(fig, [ax], x, y, lines, new_volumes, interval)
    write_video(ani, interval, filename)


def visualize_data_separately(data_list, labels, colors, interval, filename, names, start_date, timeframe):
    track_number = len(data_list)
    if track_number == 0:
        return

    length = len(data_list[0][0])
    x = np.arange(length)
    y = [data_list[i][4] for i in range(track_number)]

    fig, axs = plt.subplots(track_number, layout="tight")
    if track_number == 1:
        axs = [axs]

    for i in range(track_number):
        axs[i].set(ylabel="Price", title=(labels[i] + ' — ' + names[i]))
        data_min, data_max = np.min(data_list[i][4]), np.max(data_list[i][4])
        padding = (data_max - data_min) * 0.05
        axs[i].axis([0, len(x), data_min - padding, data_max + padding])

    fig.suptitle(f"From {start_date.split('+')[0]}, {timeframe} intervals,\n {length} points", fontsize=18)
    fig.tight_layout()

    lines = [axs[i].plot([], [], color=colors[i], label=labels[i])[0] for i in range(track_number)]
    areas = [project_data_to_range(data_list[i][5], 2, 20) for i in range(track_number)]
    for i in range(track_number):
        axs[i].scatter(x[0], y[i][0], s=areas[i][0], c=colors[i])

    ani = animate(fig, axs, x, y, lines, areas, interval)
    write_video(ani, interval, filename)


def create_final_video(audio_file, video_file, final_file):
    audio = mpe.AudioFileClip(audio_file)
    video = mpe.VideoFileClip(video_file)

    final = video.set_audio(audio)
    final.write_videofile(final_file, codec='mpeg4', audio_codec='libvorbis')


def get_data(pairs, timeframe, start, limit):
    return [parse_rates_data(pairs[i], timeframe, start, limit) for i in range(len(pairs))]


def get_pattern(data, min_pitch, max_pitch, mode, min_velocity, max_velocity, tick, resolution):
    data_len = len(data)
    pitches_list = [data_to_pitches_in_scale(data[i][4], min_pitch, max_pitch, mode) for i in range(data_len)]
    velocity_data = [project_data_to_range(data[i][5], min_velocity, max_velocity) for i in range(data_len)]

    pattern = midi.Pattern(
        (single_track_variable_volume(pitches_list[i], velocity_data[i], 1, tick) for i in range(data_len)),
        resolution,
    )
    return pattern, pitches_list, velocity_data


def parse_params():
    params = sys.argv
    start, timeframe, limit = params[1], params[2], int(params[3])
    pairs = params[4].split()
    min_pitch, max_pitch, min_velocity, max_velocity, mode = int(params[5]), int(params[6]), int(params[7]), int(params[8]), params[9]
    return start, timeframe, limit, pairs, min_pitch, max_pitch, min_velocity, max_velocity, mode


if __name__ == '__main__':
    # test_sound()

    # Parameters for making pattern
    start, timeframe, limit, pairs, min_pitch, max_pitch, min_velocity, max_velocity, mode = parse_params()
    # timeframe = '1d'
    # start = "2023-01-24 00:00:00+00:00"
    # limit = 50
    # pairs = [
    #     'BTC/USDT',
    #     'ETH/USDT',
    #     # 'SOL/USDT',
    # ]
    data = get_data(pairs, timeframe, start, limit)

    # min_pitch, max_pitch = 31, 91
    # min_velocity, max_velocity = 80, 127
    # mode = "DUR"
    tick = 100
    resolution = 100
    pattern, pitches_list, velocity_data = get_pattern(data, min_pitch, max_pitch, mode, min_velocity, max_velocity,
                                                       tick, resolution)

    audio_const = f"{min_pitch}_{max_pitch}_{min_velocity}_{max_velocity}_{mode}"
    start_date = start.split()

    time = start_date[1].split('+')[0].split(':')
    video_const = f"{start_date[0]}_{time[0]}-{time[1]}-{time[2]}_{timeframe}_{limit}"

    cryptocurrencies = '_'.join(pairs).replace('/', '-')

    const = video_const + '_' + audio_const + '_' + cryptocurrencies

    filename = "output/midi/" + const + '.mid'
    # Write the MIDI
    if pattern == -1:
        exit(-1)
    midi.write_midifile(filename, pattern)

    # r = lambda: random.randint(0, 255)
    # colors = [f'#{r():02x}{r():02x}{r():02x}' for i in range(len(pairs))]
    colors = ['red', 'green', 'blue', 'orange', 'blueviolet', 'magenta', 'lime']

    loader = sf.sf2_loader('fonts/SonificationFonts.sf2')
    # [41, 47, 74] - Violin, Harp and Flute
    # [41, 72, 13] - Violin, clarinet and marimba
    instruments = [41, 72, 13]
    instruments_names = []
    # print(loader.all_instruments())
    for i in instruments:
        # instruments_names.append(all_instruments.get(0).get(i - 1))
        instruments_names.append(loader.get_instrument_name(1, 0, i - 1))

    output_video_file = 'output/temp.mp4'
    # visualize_data(pitches_list, velocity_data, pairs, colors, tick, output_video_file)
    visualize_data_separately(data, pairs, colors, tick, output_video_file, instruments_names, start, timeframe)

    audio_file = 'output/audio/' + const
    ext = 'mp3'
    # loader.play_midi_file(current_chord=filename, instruments=[1, 72])
    loader.export_midi_file(filename, name=audio_file + '.' + ext, format=ext, instruments=instruments)

    final = 'output/video/' + const + '.mp4'
    create_final_video(audio_file + '.' + ext, output_video_file, final)
