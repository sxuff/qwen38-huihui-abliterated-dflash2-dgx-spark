#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]; s=json.loads((ROOT/'results/summary.json').read_text()); old=s['historical_control']['median_end_to_end_completion_tokens_per_second']; new=s['candidate']['median_end_to_end_completion_tokens_per_second']; ratio=s['comparison']['aggregate_median_speed_ratio']; q=s['candidate']['quality_passes']; oq=s['historical_control']['quality_passes']
img=Image.new('RGB',(1600,900),'#09111f'); d=ImageDraw.Draw(img)
def font(size,b=False):
 p='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if b else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; return ImageFont.truetype(p,size)
def text(x,y,t,f,c): d.text((x,y),t,font=f,fill=c)
d.rectangle((90,80,106,820),fill='#55e6a5'); text(150,120,'Qwen3.8-27B · ABLITERATED · NVFP4 lm_head',font(42,True),'#f5f8fc'); text(150,182,'1× NVIDIA DGX Spark · SGLang + DFlash2',font(29),'#9fb0c6'); text(150,290,'CURRENT ARA',font(27,True),'#9fb0c6'); text(150,345,f'{old:.2f}',font(100,True),'#f5f8fc'); text(150,455,'TOK/S',font(30,True),'#9fb0c6'); text(890,290,'HUIHUI-RADIXARK',font(27,True),'#55e6a5'); text(890,345,f'{new:.2f}',font(100,True),'#55e6a5'); text(890,455,'TOK/S',font(30,True),'#55e6a5'); d.line((800,280,800,540),fill='#263b55',width=2); text(615,575,f'{ratio:.2f}×',font(76,True),'#f5f8fc'); text(535,675,f'QUALITY  {oq}/27 → {q}/27',font(31,True),'#f5f8fc'); text(150,760,'27 requests · exact historical runtime image · whole-request completion rate',font(25),'#9fb0c6'); out=ROOT/'assets/qwen38-huihui-radixark-result.png'; out.parent.mkdir(exist_ok=True); img.save(out,optimize=True); print(out,img.size)
