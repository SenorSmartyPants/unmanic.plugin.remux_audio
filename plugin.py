#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               SenorSmartyPants@gmail.com and Josh.5 <jsunnex@gmail.com>
    Date:                     12 Jan 2023, (10:45 PM)

    Copyright:
        Copyright (C) 2023 SenorSmartyPants@gmail.com
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import logging
import os

from unmanic.libs.unplugins.settings import PluginSettings

from remux_audio.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.remux_audio")


class Settings(PluginSettings):
    settings = {
        "audio_codecs":         '',
        "input_file_ext":       '',
        "output_ext":           'mkv',
        "advanced":              False,
        "main_options":          '',
        "advanced_options":      ''
    }


    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "audio_codecs": {
                "label": "Comma separated list of audio codecs"
            },
            "input_file_ext": {
                "label": "Input file extentions to test"
            },
            "output_ext": {
                "label": "Output container extension"
            },
            "advanced": {
                "label": "Write your own FFmpeg params"
            },
            "main_options":          self.__set_main_options_form_settings(),
            "advanced_options":      self.__set_advanced_options_form_settings()
        }

    def __set_main_options_form_settings(self):
        values = {
            "label":      "Write your own main options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_advanced_options_form_settings(self):
        values = {
            "label":      "Write your own advanced options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, ['audio'])

        self.codec_found = False
        self.settings = None

    def set_settings(self, settings):
        self.settings = settings

    # test for audio codec
    def test_stream_needs_processing(self, stream_info: dict):
        logger.debug("File '{}' audio codec name = {}.".format(self.input_file, stream_info.get('codec_name').lower()))
        codecs = self.settings.get_setting('audio_codecs').split(',')
        codec = stream_info.get('codec_name').lower()
        if codec in codecs:
            logger.debug("audio codec {} matched!".format(codec))
            self.codec_found = True
            return True

        return False

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        #return nothing to copy all streams
        return

def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Get the path to the file
    abspath = data.get('path')

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # check that input file extension is in list to check
    exts = settings.get_setting('input_file_ext').split(',')
    split_file_in = os.path.splitext(abspath)
    if split_file_in[1].lstrip('.') not in exts:
        #don't do anything, input file extension does not match
        return data

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if 'ffprobe' in data.get('shared_info', {}):
        if not probe.set_probe(data.get('shared_info', {}).get('ffprobe')):
            # Failed to set ffprobe from shared info.
            # Probably due to it being for an incompatible mimetype declared above
            return
    elif not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return
    # Set file probe to shared infor for subsequent file test runners
    if 'shared_info' not in data:
        data['shared_info'] = {}
    data['shared_info']['ffprobe'] = probe.get_probe()

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_settings(settings)
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    # check streams for audio codecs
    mapper.streams_need_processing()
    if mapper.codec_found and mapper.container_needs_remuxing(settings.get_setting('output_ext')):
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. Probe found streams require processing.".format(abspath))
    else:
        logger.debug("File '{}' does not contain streams that require processing.".format(abspath))

    del mapper

    return data

def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:

    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # check that input file extension is in list to check
    exts = settings.get_setting('input_file_ext').split(',')
    split_file_in = os.path.splitext(abspath)
    if split_file_in[1].lstrip('.') not in exts:
        #don't do anything, input file extension does not match
        return data

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_settings(settings)
    mapper.set_probe(probe)

    # Set the input file
    mapper.set_input_file(abspath)

    # check streams for audio codecs
    mapper.streams_need_processing()
    if mapper.codec_found and mapper.container_needs_remuxing(settings.get_setting('output_ext')):
        # Set the output file
        split_file_out = os.path.splitext(data.get('file_out'))
        new_file_out = "{}.{}".format(split_file_out[0], settings.get_setting('output_ext'))
        mapper.set_output_file(new_file_out)
        data['file_out'] = new_file_out

        if settings.get_setting('advanced'):
            mapper.main_options += settings.get_setting('main_options').split()
            mapper.advanced_options += settings.get_setting('advanced_options').split()

        # Get generated ffmpeg args
        ffmpeg_args = mapper.get_ffmpeg_args()

        # Apply ffmpeg args to command
        data['exec_command'] = ['ffmpeg']
        data['exec_command'] += ffmpeg_args

        # Set the parser
        parser = Parser(logger)
        parser.set_probe(probe)
        data['command_progress_parser'] = parser.parse_progress

    return data