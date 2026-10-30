import sys, io
import fitz
from PIL import Image
from ocrmac import ocrmac

def english_ratio(s):
    letters=[c for c in s if c.isalpha()]
    if not letters: return 1.0 if any(c.isdigit() for c in s) else 0.0
    return sum(1 for c in letters if c.isascii())/len(letters)

def page_text(img):
    res = ocrmac.OCR(img, recognition_level="accurate", language_preference=["en-US"]).recognize()
    cols=[[],[]]
    for t,conf,(x,y,w,h) in res:
        cx=x+w/2
        cols[0 if cx<0.5 else 1].append((-(y+h/2),x,t))
    out=[]
    for c in cols:
        c.sort(key=lambda r:(round(r[0]/0.008),r[1]))
        out.extend(r[2] for r in c)
    return "\n".join(out)

def run(src,dst,pages=None):
    doc=fitz.open(src); parts=[]
    for i,page in enumerate(doc):
        if pages and i not in pages: continue
        pix=page.get_pixmap(matrix=fitz.Matrix(2.5,2.5),colorspace=fitz.csGRAY)
        img=Image.open(io.BytesIO(pix.tobytes("png")))
        parts.append(page_text(img))
    open(dst,"w").write("\n\f\n".join(parts))

if __name__=="__main__":
    run(sys.argv[1],sys.argv[2],{int(p) for p in sys.argv[3].split(",")} if len(sys.argv)>3 else None)
