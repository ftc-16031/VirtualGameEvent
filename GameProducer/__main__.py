#!/usr/bin/env python3
import argparse
import json
import yaml
import tempfile
import os
from os import path
from datetime import datetime
import re

# Read a game manifest file and construct ffmpeg command to produce the game video
#


parser = argparse.ArgumentParser(description='Read a game manifest file and construct ffmpeg command to produce the game video')
parser.add_argument('manifest', type=str, help='The manifest file name')
parser.add_argument('output', type=str, help='Output file name, "-" is supported to pipe to preview (such as "| ffplay -"')
args = parser.parse_args()

offset_pattern = re.compile(r'^([0-9]+):([0-9]+)$')
MAX_OFFSET = 3600

def mmss_to_seconds(mmss):
    if type(mmss) == str:
        offset_parts = offset_pattern.match(mmss)
        assert offset_parts is not None, 'Game event offset must be in "MM:SS" format'
        return int(offset_parts.group(1)) * 60 + int(offset_parts.group(2))
    else:
        # yaml automatically parse the MM:SS to seconds, but not all the time.
        return mmss


def seconds_to_hhmmss(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}.000'


class EventSrt:
    previous_event = None
    total_points = 0
    sequence = 1
    file = None
    srt_path = None

    def __init__(self, project_name, file_no):
        # fd, self.srt_path = tempfile.mkstemp(suffix='.srt', dir='.', prefix=f'{project_name}_{file_no}_', text=True)
        # TRICKY : the tempfile path doesn't work with ffmpeg subtitles filter, work around : use a file related to cwd
        self.srt_path = f'{project_name}_{file_no}.srt'
        self.file = open(self.srt_path, 'w')

    def event_text(self, event_description, point):
        if point is None:
            return f'{event_description}'
        else:
            return f'{event_description}: {point} points'

    def one_event(self, event_offset, event_description, point):
        if self.previous_event is None:
            # first event, just save it
            self.previous_event = (event_offset, [(event_offset, self.event_text(event_description, point))], point)
        else:
            previous_event_offset, previous_texts, previous_point = self.previous_event
            if previous_point is not None:
                self.total_points += previous_point
            # display previous event, but filter out older one
            self.write_one_srt('\n'.join([text for (time, text) in previous_texts if previous_event_offset - time <= 10]) + '\n', previous_event_offset, min(previous_event_offset + 10, event_offset))
            if event_offset - previous_event_offset > 10:
                # display score only in between
                self.write_one_srt('', previous_event_offset + 10, event_offset)
                # clear previous texts
                previous_texts = []

            if previous_point is None:
                # TRICKY : clear the previous texts if the previous points is None
                previous_texts = []
            self.previous_event = (event_offset, previous_texts + [(event_offset, self.event_text(event_description, point))], point)

    def flush_event(self):
        if self.previous_event is not None:
            previous_event_offset, previous_texts, previous_point = self.previous_event
            self.total_points += previous_point
            # display previous event, but filter out older one
            self.write_one_srt('\n'.join([text for (time, text) in previous_texts if previous_event_offset - time <= 10]) + '\n', previous_event_offset, previous_event_offset + 10)
        # display score only after 10 seconds
        self.write_one_srt('', previous_event_offset + 10, MAX_OFFSET)
        self.file.close()

    def write_one_srt(self, events_text, from_second, to_second):
        srt_text = f'{self.sequence}\n'
        srt_text += f'{seconds_to_hhmmss(from_second)} --> {seconds_to_hhmmss(to_second)}\n'
        srt_text += f'{events_text}'
        srt_text += f'Score: {self.total_points}\n'
        srt_text += f'\n'
        self.file.write(srt_text)
        self.sequence += 1


with open(args.manifest) as file:
    game = yaml.load(file, Loader=yaml.SafeLoader)
    project_name = path.splitext(path.basename(args.manifest))[0]
    manifest_folder = path.dirname(args.manifest)
    # validations
    assert 'VirtualGame' in game
    assert 'Name' in game['VirtualGame']
    assert 'Teams' in game['VirtualGame']
    assert 4 == len(game['VirtualGame']['Teams'])
    # iterate all teams
    start_offset = MAX_OFFSET
    alliance = {'Red': [], 'Blue': []}
    for team in game['VirtualGame']['Teams']:
        assert 'TeamName' in team
        assert 'TeamNumber' in team
        assert 'Alliance' in team
        assert team['Alliance'] in ['Red', 'Blue']
        assert 'GameVideo' in team
        assert 'Location' in team['GameVideo']
        # Tricky : try absolute path first, then fall back to relative path
        if not path.isfile(team['GameVideo']['Location']):
            assert path.isfile(path.join(manifest_folder, team['GameVideo']['Location']))
            team['GameVideo']['Location'] = path.join(manifest_folder, team['GameVideo']['Location'])
        assert 'VideoManifest' in team['GameVideo']
        if not path.isfile(team['GameVideo']['VideoManifest']):
            assert path.isfile(path.join(manifest_folder, team['GameVideo']['VideoManifest']))
            team['GameVideo']['VideoManifest'] = path.join(manifest_folder, team['GameVideo']['VideoManifest'])
        with open(team['GameVideo']['VideoManifest']) as video_manifest_file:
            team['GameVideo']['VideoManifest'] = yaml.load(video_manifest_file, Loader=yaml.SafeLoader)
        assert 'GameStartOffset' in team['GameVideo']['VideoManifest']
        offset_seconds = mmss_to_seconds(team['GameVideo']['VideoManifest']['GameStartOffset'])
        start_offset = min(start_offset, offset_seconds)
        team['GameVideo']['GameStartOffsetInSecond'] = offset_seconds
        assert 'GameEvents' in team['GameVideo']['VideoManifest']
        previous_event_time = 0
        for event in team['GameVideo']['VideoManifest']['GameEvents']:
            assert 'Time' in event
            event['TimeInSeconds'] = mmss_to_seconds(event['Time'])
            # assure the events are in order
            assert previous_event_time <= event['TimeInSeconds']
            previous_event_time = event['TimeInSeconds']
            assert 'Description' in event
            assert 'Point' in event
            event['Point'] = int(event['Point'])
        alliance[team['Alliance']].append(team)
    assert start_offset < 1000
    assert len(alliance['Blue']) == 2
    assert len(alliance['Red']) == 2
    # generate subtitles
    file_no = 0
    for team in alliance['Blue'] + alliance['Red']:
        video_start_offset = team["GameVideo"]["GameStartOffsetInSecond"] - start_offset
        team['GameVideo']['PlayStartOffset'] = video_start_offset
        srt = EventSrt(project_name, file_no)
        srt.one_event(start_offset, 'Game Start!', None)
        for event in team['GameVideo']['VideoManifest']['GameEvents']:
            srt.one_event(event["TimeInSeconds"] - video_start_offset, event["Description"], event["Point"])
        srt.flush_event()
        team['GameVideo']['GameScoreSubtitle'] = srt.srt_path
        print(f"Generated subtitles {srt.srt_path} for [#{team['TeamNumber']}, {team['TeamName']}] from game manifest")
        file_no += 1

    # generate ffmpeg command
    ffmpeg_command = 'ffmpeg'
    filter_subtitles = ''
    i = 0
    for team in alliance['Blue']:
        ffmpeg_command += f' -ss {team["GameVideo"]["GameStartOffsetInSecond"] - start_offset} -i "{team["GameVideo"]["Location"]}"'
        filter_subtitles +=f'[{i}:v]scale=640:480[v{i}n]; '
        filter_subtitles +=f'[v{i}n]subtitles=filename={team["GameVideo"]["GameScoreSubtitle"].__repr__()}:force_style=\'Fontsize=16\'[v{i}s]; '
        filter_subtitles +=f'[v{i}s]drawtext=text=\'FTC #{team["TeamNumber"]}\':fontcolor=white:fontsize=18:box=1: boxcolor=black@0.5:boxborderw=5:x=20:y=10[v{i}s]; '
        filter_subtitles +=f'[v{i}s]drawtext=text=\'{team["TeamName"]}\':fontcolor=white:fontsize=18:box=1: boxcolor=black@0.5:boxborderw=5:x=20:y=40[v{i}s]; '
        i += 1
    for team in alliance['Red']:
        ffmpeg_command += f' -ss {team["GameVideo"]["GameStartOffsetInSecond"] - start_offset} -i "{team["GameVideo"]["Location"]}"'
        filter_subtitles +=f'[{i}:v]scale=640:480[v{i}n]; '
        filter_subtitles +=f'[v{i}n]subtitles=filename={team["GameVideo"]["GameScoreSubtitle"].__repr__()}:force_style=\'Fontsize=16\'[v{i}s]; '
        filter_subtitles +=f'[v{i}s]drawtext=text=\'FTC #{team["TeamNumber"]}\':fontcolor=white:fontsize=18:box=1: boxcolor=black@0.5:boxborderw=5:x=(w-text_w)-20:y=10[v{i}s]; '
        filter_subtitles +=f'[v{i}s]drawtext=text=\'{team["TeamName"]}\':fontcolor=white:fontsize=18:box=1: boxcolor=black@0.5:boxborderw=5:x=(w-text_w)-20:y=40[v{i}s]; '
        i += 1
    ffmpeg_command +=f' -filter_complex "{filter_subtitles} ' \
                     f'[v0s][v1s]vstack[left]; [v2s][v3s]vstack[right]; ' \
                     f'[left]pad=iw+10:ih+10:5:5:color=blue[left]; [right]pad=iw+10:ih+10:5:5:color=red[right]; ' \
                     f"[left]drawtext=text='Blue Alliance':fontcolor=blue:fontsize=24:box=1: boxcolor=orange@0.9:boxborderw=5:x=(w-text_w)-20:y=h/2-10[left]; " \
                     f"[right]drawtext=text='Red Alliance':fontcolor=red:fontsize=24:box=1: boxcolor=orange@0.9:boxborderw=5:x=20:y=h/2-10[right]; " \
                     f'[left][right]hstack[v]; ' \
                     f'[0:a][1:a]amerge[a]; [a][2:a]amerge[a]; [a][3:a]amerge[a]"' \
                     f' -map "[v]" -map "[a]" -f matroska' \
                     f' "{args.output}"'
    print(ffmpeg_command)
    os.system(ffmpeg_command)

    # remove the temporary srt files
    for team in alliance['Blue']:
        os.remove(team["GameVideo"]["GameScoreSubtitle"])
    for team in alliance['Red']:
        os.remove(team["GameVideo"]["GameScoreSubtitle"])

