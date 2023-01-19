
---

#### <span style="color:blue">Write your own FFmpeg params</span>
This free text input allows you to write any FFmpeg params that you want.
This is for more advanced use cases where you need finer control over the file transcode.

:::note
These params are added in three different places:
1. **MAIN OPTIONS** - After the default generic options.
   ([Main Options Docs](https://ffmpeg.org/ffmpeg.html#Main-options))
1. **ADVANCED OPTIONS** - After the input file has been specified.
   ([Advanced Options Docs](https://ffmpeg.org/ffmpeg.html#Advanced-options))

```
ffmpeg \
    -hide_banner \
    -loglevel info \
    <MAIN OPTIONS HERE> \
    -i /path/to/input/video.mkv \
    <ADVANCED OPTIONS HERE> \
    -map 0 \
    -c copy \
    -y /path/to/output/video.mkv
```
:::

---