#!/bin/bash
set -e
S=/tmp/claude-0/-home-user-Claude-mobile-test-/4aa42345-96bf-5298-9600-802b21be64c8/scratchpad
U=/root/.claude/uploads/4aa42345-96bf-5298-9600-802b21be64c8
P1=$U/9a458922-Untitled_Artwork.mov; P2=$U/2bc07eab-Untitled_Artwork.mov; P4=$U/edfa197e-Untitled_Artwork.mov
I=/tmp/claude-0/-home-user-Claude-mobile-test-/4aa42345-96bf-5298-9600-802b21be64c8/images
A=$I/1.webp; B=$I/2.jpg
O=$S/seg; cd $O
ENC="-r 30 -c:v libx264 -preset veryfast -crf 14 -pix_fmt yuv420p -an"
FIT="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
SWAP="colorchannelmixer=rr=0:rb=1:bb=0:br=1"
FLASH="negate=enable='lt(n,2)'"
SHAKE="crop=1000:1778:x='40+28*sin(n*1.7)*sin(n*0.31)':y='71+28*cos(n*2.3)',scale=1080:1920"
PULSE="scale=w='trunc(1080*(1+0.10*exp(-mod(t,0.5)*9))/2)*2':h='trunc(1920*(1+0.10*exp(-mod(t,0.5)*9))/2)*2':eval=frame,crop=1080:1920"
still(){ ffmpeg -v error -y -loop 1 -framerate 30 -t $2 -i $1 -vf "$FIT,scale=2160:3840,zoompan=z='$3':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30,$4" $ENC -t $2 $5; }
# proc: src start len speed outdur extra out  (tracing reference removed via degrey.py)
proc(){ ffmpeg -v error -ss $2 -t $3 -i $1 -vf "setpts=PTS/$4,fps=30,$FIT" -f rawvideo -pix_fmt rgb24 - | python3 $S/degrey.py | \
  ffmpeg -v error -y -f rawvideo -pix_fmt rgb24 -s 1080x1920 -r 30 -i - -vf "$6" $ENC -t $5 $7; }
still $A 0.5 "max(1.9-0.06*on,1)" "rgbashift=rh=-18:bh=18,$FLASH" s01.mp4
still $A 0.5 "1.15" "$SWAP,$SHAKE,$FLASH" s02.mp4
proc $P1 0 60.5 20 3 "$PULSE,$FLASH" s03.mp4
still $B 1.0 "1+0.012*on" "$SHAKE,rgbashift=rh=10:bv=10,$FLASH" s04.mp4
proc $P2 0 60 24 2.5 "$PULSE,rgbashift=rh=-10:bh=10:enable='lt(mod(t,0.5),0.07)',$FLASH" s05.mp4
for k in 0 1 2 3 4 5 6 7; do case $((k%4)) in
  0) still $A 0.25 "1.05" "null" st$k.mp4;; 1) still $A 0.25 "1.12" "$SWAP" st$k.mp4;;
  2) still $B 0.25 "1.0+0.04*on" "null" st$k.mp4;; 3) still $A 0.25 "1.2" "negate,$SHAKE" st$k.mp4;; esac; done
ffmpeg -v error -y -ss 30 -t 7.5 -i $P4 -vf "setpts=PTS/5,fps=30,$FIT,$PULSE,$FLASH" $ENC -t 1.5 s07.mp4
w=0; for c in "540:690" "560:905" "470:1085" "520:1290"; do cx=${c%:*}; cy=${c#*:}
 ffmpeg -v error -y -loop 1 -framerate 30 -t 0.75 -i $A -vf "$FIT,scale=2160:3840,zoompan=z='2.6-0.02*on':x='$cx*2-iw/zoom/2':y='$cy*2-ih/zoom/2':d=1:s=1080x1920:fps=30,$( [ $((w%2)) = 1 ] && echo "$SWAP," )rgbashift=rh=-8:bh=8,$FLASH" $ENC -t 0.75 w$w.mp4; w=$((w+1)); done
ffmpeg -v error -y -ss 53 -t 6 -i $P4 -vf "setpts=PTS/6,fps=30,$FIT,split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1,$PULSE,$FLASH" $ENC -t 2 s09.mp4
still $B 0.5 "1+0.09*on" "rgbashift=rh=-12:bh=12,$FLASH" s10.mp4
ffmpeg -v error -y -loop 1 -framerate 30 -t 0.5 -i $A -vf "$FIT,split[n][s];[s]$SWAP[sw];[n][sw]blend=all_expr='if(eq(mod(floor(N/2),2),1),B,A)',$FLASH" $ENC -t 0.5 s11.mp4
ffmpeg -v error -y -loop 1 -framerate 30 -t 3 -i $A -vf "$FIT,scale=2160:3840,zoompan=z='1+0.001*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30,eq=contrast=1.06:saturation=1.1,$FLASH" $ENC -t 3 s12.mp4
printf "file '%s'\n" s01.mp4 s02.mp4 s03.mp4 s04.mp4 s05.mp4 st0.mp4 st1.mp4 st2.mp4 st3.mp4 st4.mp4 st5.mp4 st6.mp4 st7.mp4 s07.mp4 w0.mp4 w1.mp4 w2.mp4 w3.mp4 s09.mp4 s10.mp4 s11.mp4 s12.mp4 > list.txt
ffmpeg -v error -y -f concat -safe 0 -i list.txt -vf "noise=alls=8:allf=t,vignette=PI/5,format=yuv420p" -r 30 -c:v libx264 -preset slow -crf 19 -maxrate 14M -bufsize 28M -profile:v high -movflags +faststart -t 20 $S/reel.mp4
ffprobe -v error -show_entries format=duration:stream=width,height -of compact $S/reel.mp4
