
#!/bin/bash

mkdir -p notes

count=0

for start in $(seq 0 0.2 11.8)
do
    ffmpeg -loglevel error \
        -ss "$start" \
        -t 0.5 \
        -i viacheslavstarostin-gaming-game-video-game-music-474517.mp3 \
        -af "afade=t=in:st=0:d=0.005,afade=t=out:st=0.17:d=0.03" \
        "notes/note_$(printf "%03d" $count).wav" \
        -y

    ((count++))
done

echo "Created $count notes."
