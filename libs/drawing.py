from Bio import GenBank
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import black, white, HexColor
from loaders import load_genbank
from config import fct_flags, fct_colors, idpt
from array_tetris import offset_coord, nudge_coord

### Hardcoded presets ###
## General proportions ##
u 		= 0.0125		# conversion factor for sequence length-related values (0.0125, increase for short sequences)
hmar 	= 1*cm			# horizontal margin to canvas (1*cm)
vmar 	= 2*cm			# vertical margin to canvas (2*cm)
pNsize 	= 4*cm			# width to set aside for plasmid names (2.5*cm)
di 		= 0.18*cm		# half-length of interruption/frameshift tick marks (0.18*cm)
doL 	= 0.7*cm		# distance of ORF labels from their ORF (0.7*cm)
minL 	= 700			# minimum ORF size (in base pairs) for 'full arrows' (700, decrease for short seq)
w 		= 0.3*cm     	# half-width of the tail (0.3*cm)
h 		= 0.175*cm		# distance from the side tips of the head to the neck (0.175*cm)
dBL	 	= 3*cm			# distance between plasmid baselines (4*cm)
da 		= 0.4*cm		# distance of alignment tick marks from the corresponding plasmid baseline (0.4*cm)
ck_hsp 	= 170		    # horizontal spacing between columns (170)
ck_vsp 	= 17		    # vertical spacing between items (17)
tm 		= 0.2*cm		# size of alignment tick marks (0.2*cm)
y_adj   = -4.2*cm       # vertical adjustment factor

## Typeface, fonts, sizes ##
rFont 	= "Helvetica"			# regular type ("Helvetica")
bFont 	= "Helvetica-Bold"		# bold type ("Helvetica-Bold")
LfSize 	= 14					# large font size (14)
NfSize 	= 12					# normal font size (12)
SfSize 	= 10					# small font size (10)

## Special feature settings ##
SFX 	= 'off'			# allow drawing special sequence features beside CDS/ORF ('on' or 'off')
osym 	= '*'			# symbol for origin of sequence (*)
snp		= '*'			# symbol for SNP (*)

## Scale of sequence, in legend ##
scX 	= 0*u			# starting point on the X axis(0)
incrT 	= 1000*u		# increment size in basepairs (1000, signifying 1 kb)
incrN 	= 5				# increment number (5, or 1 for short sequences)
dip 	= -2*cm			# starting point on Y axis (-2*cm)
dop 	= 0.3*cm		# size of vertical tick

## Canvasser : Initialize canvas ##
def Canvasser(hCan,vCan,transX,transY,outfile) :
    canvasN = canvas.Canvas(outfile, pagesize=(hCan,vCan))
    canvasN.translate(transX,transY)
    canvasN.setStrokeColor(black)
    canvasN.setFillColor(white)
    canvasN.setLineWidth(1)
    canvasN.setLineJoin(1)
    canvasN.setLineCap(0)
    return canvasN

def BaseDraw(canvas, cName, cLen, feats, key, dop_Y, Y0, X_shift,
             map_mode, annot_cnt, offset, offset_mode) :
    """Draw contig baseline and features."""
    # draw plasmid baseline
    BaseL(cLen, canvas, Y0, offset, offset_mode)
    # label the baseline with plasmid name and size
    LabeL(cName, cLen, canvas, Y0)
    # label the annotations list
    Y_annot = 0
    canvas.drawString(X_shift, y_adj, cName)
    Y_annot +=2
    # filter and draw annotation features
    ORFcnt = 0
    shift_flag = False
    for feature in feats :
        if feature.type == 'contig':
            TigTicker(canvas, feature, cLen, offset, offset_mode)
        if feature.type == 'CDS' or feature.type == 'cds':
            ORFcnt += 1
            # determine functional category color
            annot = feature.qualifiers.get(key)[0]
            fct_key = annot_color(fct_flags, annot)
            color_hex = HexColor(fct_colors[fct_key][0])
            # calculate coordinates for canvas
            featL, midLZ, coords, split_flag = ORFcoords(feature, Y0, cLen,
                                                         offset, offset_mode)
            # check for CDS sitting across the origin
            if split_flag:
                # split coords
                coords1, featL1, coords2, featL2 = ORFsplit(coords, cLen)
                # draw square feature
                ORFeus(canvas, featL1, coords1, color_hex, shape='square')
                # draw arrow feature
                ORFeus(canvas, featL2, coords2, color_hex, shape=None)
            else:
                # draw arrow feature
                ORFeus(canvas, featL, coords, color_hex, shape=None)
            # write annotation line and CDS number
            if map_mode == 'single' and Y_annot > annot_cnt/2:
                X_shift = (cLen/2)*u
                if not shift_flag:
                    Y_annot -= annot_cnt/2
                    shift_flag = True
            Y_annot = ORFannot(canvas, cLen, annot, Y_annot, ORFcnt, Y0+dop_Y,
                               midLZ,
                               X_shift, split_flag)

## BaseL : Draws phage baselines ##
def BaseL(cLen, canvas, Y_map, offset, offset_mode) :
    canvas.setLineWidth(3)
    y0 = Y_map
    Zs = 0              # all sequences are initially aligned on the left
    Ze = cLen
    # calculate offsets
    if offset_mode == 'nudge':
        offZs = nudge_coord(Zs, offset)
        offZe = nudge_coord(Ze, offset)
    else:
        offZs = Ze
        offZe = Zs
    x0 = offZs*u
    x1 = offZe*u
    pBL = canvas.beginPath()
    pBL.moveTo(x0,y0)
    pBL.lineTo(x1,y0)
    canvas.drawPath(pBL, stroke=1, fill=0)
    pBL.close()

## LabeL : Labels baselines with plasmid name and size ##
def LabeL(cName, cLen, canvas, Y_map) :
    canvas.setFillColor(black)
    y0 = Y_map
    x0 = -pNsize                # retreat into the left margin to write out name and size
    y1 = y0 + ck_vsp/10         # bump name up a bit from BL level
    y2 = y0 - ck_vsp            # bump size down a bit from BL level
    pLenStr = str(float(cLen)/1000) # converts number to suitable form
    canvas.setFont(bFont,LfSize)
    canvas.drawString(x0,y1,cName)
    canvas.setFont(rFont,NfSize)
    canvas.drawString(x0,y2,pLenStr+' kb')

def ORFannot(canvas, cLen, annot, Y_annot, ORFcnt, cnt_Y, midLZ, X_shift,
             split_flag):
    """Write annotation to feature list."""
    if annot == 'no match' or \
       annot == 'hypothetical protein' or \
       annot[:5] == 'pXO1-': # quick fix
        pass
    else:
        # write CDS numbers
        if split_flag:
            canvas.drawCentredString(1*u, cnt_Y, "]"+str(ORFcnt))
            canvas.drawCentredString(cLen*u, cnt_Y, str(ORFcnt)+"[")
        else:
            canvas.drawCentredString(midLZ, cnt_Y, str(ORFcnt))
        # write annotation
        y_annot_adj = y_adj-(Y_annot*ck_vsp)
        canvas.setFont(rFont, SfSize)
        canvas.drawString(X_shift, y_annot_adj, str(ORFcnt)+'. '+annot)
        canvas.setFont(rFont, NfSize)
        Y_annot +=1
    return Y_annot

def ORFcoords(feature, Y_map, cLen, offset, offset_mode):
    """Calculate CDS coordinates in drawing space."""
    # evaluate what strand the ORF is on (determines direction of arrow)
    cstrand = feature.strand
    if cstrand is None:
        cstrand = 1
    # take start and end points
    location = feature.location
    Zs = location.nofuzzy_start
    Ze = location.nofuzzy_end
    featL = Ze - Zs
    # calculate offset coordinates
    if offset_mode == 'offset':
        Zs = offset_coord(Zs, cLen, offset)
        Ze = offset_coord(Ze, cLen, offset)
    elif offset_mode == 'nudge':
        Zs = nudge_coord(Zs, offset)
        Ze = nudge_coord(Ze, offset)
    else:
        pass
    # calculate X axis coordinates (expr of cstrand has changed)
    if cstrand == -1 :	# reverse orientation
        xs,xe = Ze*u,Zs*u		# start and end
        xn = xe+minL*u		# neck of arrow
    else :				# forward orientation
        xs,xe = Zs*u,Ze*u		# start and end
        xn = xe-minL*u		# neck of arrow
    midLZ = ((Zs+Ze)/2)*u	# middle of ORF for optional label
    # evaluate splits
    split_flag = False
    if (xs < xe and cstrand == -1) or (xs > xe and cstrand == 1):
        midLZ = 0
        split_flag = True
    # set Y axis coordinates
    y0 = Y_map
    yt,yb,ynt,ynb = y0+w,y0-w,y0+h,y0-h
    coords = xs, xe, xn, y0, yt, yb, ynt, ynb
    return featL, midLZ, coords, split_flag

def ORFsplit(coords, cLen):
    """Split CDS that sit across the map origin."""
    xs, xe, xn, y0, yt, yb, ynt, ynb = coords
    if xs < xe:
        coords1 = xs, 1*u, xn, y0, yt, yb, ynt, ynb
        coords2 = cLen*u, xe, xn, y0, yt, yb, ynt, ynb
        featL1 = xs/u
        featL2 = cLen-xe/u
    else:
        coords1 = xs, cLen*u, xn, y0, yt, yb, ynt, ynb
        coords2 = 1*u, xe, xn, y0, yt, yb, ynt, ynb
        featL1 = cLen-xs/u
        featL2 = xe/u
    return coords1, featL1, coords2, featL2

def ORFeus(canvas, featL, coords, color_hex, shape):
    """Draw CDS and write count."""
    xs, xe, xn, y0, yt, yb, ynt, ynb = coords
    canvas.setLineWidth(1)
    # initialize path
    pORF = canvas.beginPath()
    if shape == 'square':
        pORF.moveTo(xs,ynt)
        pORF.lineTo(xe,ynt)
        pORF.lineTo(xe,ynb)
        pORF.lineTo(xs,ynb)
        pORF.lineTo(xs,ynt)
    # draw triangle-shaped ORFS
    elif featL <= minL:
        pORF.moveTo(xs,yt)
        pORF.lineTo(xe,y0)
        pORF.lineTo(xs,yb)
        pORF.lineTo(xs,yt)
    # draw arrow-shaped ORFS
    else:
        pORF.moveTo(xs,ynt)
        pORF.lineTo(xn,ynt)
        pORF.lineTo(xn,yt)
        pORF.lineTo(xe,y0)
        pORF.lineTo(xn,yb)
        pORF.lineTo(xn,ynb)
        pORF.lineTo(xs,ynb)
        pORF.lineTo(xs,ynt)
    # evaluate function category and set fill color
    canvas.setFillColor(color_hex)
    # finalize object path
    canvas.drawPath(pORF, stroke=1, fill=1)
    pORF.close()
    canvas.setFillColor(black)

def TigTicker(canvas, feature, cLen, offset, offset_mode):
    """Draw contig separators."""
    # get contig name
    name = feature.qualifiers.get('id')[0]
    # take start and end points
    location = feature.location
    Zs = location.nofuzzy_start
    Ze = location.nofuzzy_end
    # calculate offset coordinates
    if offset_mode == 'offset':
        offZs = offset_coord(Zs, cLen, offset)
        offZe = offset_coord(Ze, cLen, offset)
    elif offset_mode == 'nudge':
        offZs = nudge_coord(Zs, offset)
        offZe = nudge_coord(Ze, offset)
    else:
        offZs = Zs
        offZe = Ze
    xs, xe = offZs*u, offZe*u
    # set Y axis coordinates
    y0 = (h+dop)*2
    # draw
    canvas.setLineWidth(2)
    ttl = canvas.beginPath()
    ttl.moveTo(xs,y0)
    ttl.lineTo(xs,y0-h*2.5)
    ttl.lineTo(xs+dop,y0-h*2.5)
    canvas.drawPath(ttl, stroke=1, fill=0)
    canvas.setFont(rFont, NfSize)
    canvas.drawString(xs+dop*2, y0-h*3, name)
    canvas.setFont(rFont, SfSize)
    canvas.drawString(xs+dop*2,y0-h*6,"".join(["[",str(Zs),"-",str(Ze),"]"]))
    canvas.setFont(rFont, NfSize)
    ttl.close()

def SeqScale(canvas, scX, incrT, incrN, dip, dop) :
    """Draws the sequence scale bar."""
    canvas.setLineWidth(1.2)
    canvas.setFillColor(black)
    incrCNT = 0							# initialize count of increments
    psc = canvas.beginPath()
    psc.moveTo(scX,dip-dop)				# start at beginning (duh!)
    psc.lineTo(scX+incrT*incrN,dip-dop)	# draw the scale baseline
    # draw ticks until the max number of increments is reached
    while incrCNT <= incrN :
        psc.moveTo(scX+incrT*incrCNT,dip-dop)
        psc.lineTo(scX+incrT*incrCNT,dip)
        incrCNT += 1
    canvas.drawPath(psc, stroke=1, fill=0)
    psc.close()
    # write out scale extremities values (needs hand-fix if not using kbs)
    canvas.setFont(rFont,NfSize)
    canvas.drawRightString(scX,dip+dop,'0')
    canvas.drawString(scX+incrT*incrN,dip+dop,str(incrN)+' kb')

def annot_color(fct_flags, annotation):
    """Look up the color to use based on annotation keywords."""
    annot_line = annotation.lower()
    fct_key = 'oth'
    for key in fct_flags:
        i = 0
        while i < len(fct_flags[key]):
            if annot_line.find(fct_flags[key][i]) > -1:
                fct_key = key
                break
            i +=1
    return fct_key

def ContigDraw(cName, in_file, out_file):
    """Draw sequence map of a single contig to file."""
    # load contig record
    seq_record = load_genbank(in_file)
    ctg_len = len(seq_record.seq)
    feats = seq_record.features
    cds = [feature for feature in feats
           if feature.type == 'CDS' or feature.type == 'cds']
    annot_cds = [1 for feature in cds
                 if feature.qualifiers.get('fct')[0] != 'no match']
    annot_cnt = sum(annot_cds)
    # calculate main canvas dimensions
    if ctg_len < 25000:
        hCan = 32*cm
    else:
        hCan = hmar*2 + pNsize + ctg_len*u
    vCan = dBL + vmar*4 + (annot_cnt/2)*ck_vsp
    transX = hmar + pNsize
    transY = dBL + vmar*2 + (annot_cnt/2)*ck_vsp
    ctg_Y = vmar
    # set up main canvas
    canvas = Canvasser(hCan, vCan, transX, transY, out_file)
    # draw contig baseline and features
    BaseDraw(canvas, cName, ctg_len, feats, 'fct', -doL, ctg_Y, 0, 'single',
             annot_cnt, None, None)
    # draw scale
    SeqScale(canvas, (ctg_len*u)-pNsize, incrT, incrN, dip, dop )
    # write to file and finalize the figure
    canvas.showPage()
    canvas.save()

def PairwiseDraw(ref_name, q_name, q_file, ref_file, segs, map_file, q_inv,
                 g_offset):
    """Draw pairwise alignment map with similarity shading."""
    # load ref and query records
    # ref first
    ref_record = load_genbank(ref_file)
    ref_len = len(ref_record.seq)
    ref_feat = ref_record.features
    ref_cds = [feature for feature in ref_feat
               if feature.type == 'CDS' or feature.type == 'cds']
    ref_annot_cds = [1 for feature in ref_cds
                     if feature.qualifiers.get('product')[0] !=
                        'hypothetical protein' and \
                        feature.qualifiers.get('product')[0][:5] !=
                        'pXO1-']
    ref_annot_cnt = sum(ref_annot_cds)
    # now query
    query_record = load_genbank(q_file)
    if q_inv:
        query_record = query_record.reverse_complement()
    q_len = len(query_record.seq)
    q_feat = query_record.features
    query_cds = [feature for feature in q_feat
                 if feature.type == 'CDS' or feature.type == 'cds']
    query_annot_cds = [1 for feature in query_cds
                       if feature.qualifiers.get('fct')[0] != 'no match']
    query_annot_cnt = sum(query_annot_cds)
     # calculate main canvas dimensions
    if ref_len > q_len:
        ctg_len = ref_len+g_offset[0]
    else:
        ctg_len = q_len
    annot_cnt = max(ref_annot_cnt, query_annot_cnt)
    if ctg_len < 50000:
        hCan = 32*cm
    else:
        hCan = hmar*2 + pNsize + ctg_len*u
    vCan = dBL + vmar*6 + annot_cnt*ck_vsp
    transX = hmar + pNsize
    transY = dBL + vmar*2 + annot_cnt*ck_vsp
    ref_Y = vmar*3
    query_Y = vmar
    # set up main canvas
    m_canvas = Canvasser(hCan, vCan, transX, transY, map_file)
    # draw scale
    SeqScale(m_canvas, (ctg_len*u)-pNsize, incrT, incrN, dip, dop )
    # draw ref baseline and features
    BaseDraw(m_canvas, ref_name, ref_len, ref_feat, 'product', doL, ref_Y,
             0, 'dual', annot_cnt, g_offset[0], 'nudge')
    # draw query baseline and features
    BaseDraw(m_canvas, q_name, q_len, q_feat, 'fct', -doL, query_Y,
             q_len*u/2, 'dual', annot_cnt, g_offset[1], 'offset')
    # draw pairwise similarity shading
    for xa, xb, xc, xd, idp in segs:
        # evaluate color shading category
        sh_color = HexColor(SimColor(idp))
        # check for split
        if abs(xa) > abs(xb) or abs(xc) > abs(xd):
            coords1, coords2 = shade_split(xa, xb, xc, xd, q_len)
            xa1, xb1, xc1, xd1 = coords1
            xa2, xb2, xc2, xd2 = coords2
            # draw shading
            Shadowfax(m_canvas, xa1, xb1, xc1, xd1, ref_Y, query_Y, sh_color)
            Shadowfax(m_canvas, xa2, xb2, xc2, xd2, ref_Y, query_Y, sh_color)
        else:
            # draw shading
            Shadowfax(m_canvas, xa, xb, xc, xd, ref_Y, query_Y, sh_color)
    # write to file and finalize the figure
    m_canvas.showPage()
    m_canvas.save()

def Shadowfax(canvas_def, xa, xb, xc, xd, aby0, cdy0, sh_color):
    """Draw shaded area between homologous segments."""
    canvas_def.setLineWidth(1)
    # convert sequence-scale values to canvas-space
    axr, bxr, cxr, dxr = xa*u, xb*u, xc*u, xd*u
    # check for negatives that need to be flipped
    ax, bx = Flipper(axr,bxr)
    cx, dx = Flipper(cxr,dxr)
    # these are the actual Y coordinates that will be used to draw the cues
    aby1 = aby0-da
    aby2 = aby1-tm
    cdy1 = cdy0+da
    cdy2 = cdy1+tm
    # this draws the parallelograms between matching segments
    canvas_def.setLineWidth(1)
    canvas_def.setFillColor(sh_color)
    ppg = canvas_def.beginPath()
    ppg.moveTo(ax,aby2)
    ppg.lineTo(bx,aby2)
    ppg.lineTo(dx,cdy2)
    ppg.lineTo(cx,cdy2)
    ppg.lineTo(ax,aby2)
    canvas_def.drawPath(ppg, stroke=0, fill=1)
    ppg.close()
    # this draws the tick marks and lines delineating matching segments
    canvas_def.setLineWidth(1)
    puck = canvas_def.beginPath()
    puck.moveTo(ax,aby1)
    puck.lineTo(ax,aby2)
    puck.lineTo(cx,cdy2)
    puck.lineTo(cx,cdy1)
    puck.moveTo(bx,aby1)
    puck.lineTo(bx,aby2)
    puck.lineTo(dx,cdy2)
    puck.lineTo(dx,cdy1)
    canvas_def.drawPath(puck, stroke=1, fill=0)
    puck.close()

def shade_split(xa, xb, xc, xd, q_len):
    """Split shaded areas that sit across the map origin.

    This assumes that xa -> xb is always non-split since it is on the
    reference, which is treated as linear, not circular. It also assumes that
    only reference-side segments can be of negative sign.
    """
    if xa > 0:
        xa1, xb1, xc1, xd1 = xa, xa+q_len-xc, xc, q_len
        xa2, xb2, xc2, xd2 = xa+q_len-xc, xb, 1, xd
    else: # xa <0
        xa1, xb1, xc1, xd1 = xa, xa-xd, 1, xd
        xa2, xb2, xc2, xd2 = xa-xd, xb, xc, q_len
    coords1 = xa1, xb1, xc1, xd1
    coords2 = xa2, xb2, xc2, xd2
    return coords1, coords2

def Flipper(axr,bxr) :
    """Flip negative coordinates."""
    if axr < 0 :
        ax,bx = abs(bxr),abs(axr)
    else :
        ax,bx = axr,bxr
    return ax,bx

def SimColor(idp) :
    """Evaluate class of similarity."""
    id_cats = [x for x in idpt if idp>=x]
    sh_hex = idpt[max(id_cats)]
    return sh_hex












