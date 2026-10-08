"""Build an original experimental sound from the user's exported Init JSON.

No factory patch is used as a sound template. Module/destination structures are
cross-checked against local exports; UI mapping and playback need Serum checks.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).parent
source = ROOT / 'Init_New_Design_Source.json'
assert hashlib.sha256(source.read_bytes()).hexdigest() == '21e4888bea6035e498f81b4a1a4a15bb9c58c29d5519103038ef5b91439a3e6b'
document = json.loads(source.read_text())
d = document['data']
refs = json.loads((ROOT / 'Neurospore_destination_references.json').read_text())
changes = []

def put(key, value):
    changes.append(key)
    d[key] = value

def table(name, frame_count, make_frame):
    samples = []
    for frame in range(frame_count):
        t = frame / max(1, frame_count - 1)
        values = [make_frame(t, 2 * math.pi * n / 2048) for n in range(2048)]
        mean = sum(values) / len(values)
        values = [x - mean for x in values]
        peak = max(abs(x) for x in values)
        samples.extend([x * 0.92 / max(peak, 1e-12) for x in values])
    audio = struct.pack('<%df' % len(samples), *samples)
    fmt = struct.pack('<HHIIHH', 3, 1, 44100, 44100 * 4, 4, 32)
    clm = b'<!>2048 01000000 wavetable (www.xferrecords.com)'
    def chunk(tag, data):
        return tag + struct.pack('<I', len(data)) + data + (b'\0' if len(data) % 2 else b'')
    body = b'WAVE' + chunk(b'fmt ', fmt) + chunk(b'clm ', clm) + chunk(b'data', audio)
    (ROOT / (name + '.wav')).write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)
    return {'embeddedWTData': samples, 'flex': {}, 'interpolateAfterLoad': 0,
            'numChannels': 1, 'numFrames': len(samples), 'sampleRate': 44100,
            'tableDisplayName': name, 'plainParams': {}}

def vowel(t, phase):
    centers = (3 + 8*t, 12 - 5*t, 18 + 9*t)
    return sum((0.13/h + sum(a * math.exp(-0.5*((h-c)/w)**2)
               for a,c,w in zip((0.75,0.45,0.23),centers,(1.0,1.5,2.0))))
               * math.sin(h*phase + 0.08*t*h) for h in range(1,33))

def metallic(t, phase):
    return sum((0.22/h + 0.8*math.exp(-0.5*((h-(5+18*t))/1.7)**2))
               * math.sin(h*phase + 0.55*math.sin(h*1.37+t*2*math.pi))
               for h in range(1,33))

tables = [table('Neurospore Formant Spine',32,vowel),
          table('Neurospore FM Sine',1,lambda t,p: math.sin(p)),
          table('Neurospore Metallic Teeth',16,metallic)]
# The file's WT-position coordinate is retained as serialized state, not
# represented as a verified frame index. Local files use the 1..256 coordinate.
tables[0]['plainParams'] = {'kParamTablePos': 44.0, 'kParamWarpMenu': 'kFM_OSC',
                           'kParamWarp': 0.12, 'kParamInitialPhase': 0.0,
                           'kParamRandomPhase': 0.0}
tables[1]['plainParams'] = {'kParamTablePos': 1.0, 'kParamInitialPhase': 0.0,
                           'kParamRandomPhase': 0.0}
tables[2]['plainParams'] = {'kParamTablePos': 92.0, 'kParamInitialPhase': 90.0,
                           'kParamRandomPhase': 18.0}
for i, params in enumerate([
    {'kParamEnable':1., 'kParamOctave':0., 'kParamUnison':1., 'kParamVolume':0.62},
    {'kParamEnable':1., 'kParamOctave':2., 'kParamUnison':1., 'kParamVolume':0.0},
    {'kParamEnable':1., 'kParamOctave':1., 'kParamUnison':2., 'kParamDetune':0.012,
     'kParamDetuneWid':65., 'kParamVolume':0.20},
]):
    osc = copy.deepcopy(d['Oscillator'+str(i)])
    osc['plainParams'] = params
    osc['WTOsc'+str(i)] = tables[i]
    put('Oscillator'+str(i), osc)
for i in (3,4):
    osc = copy.deepcopy(d['Oscillator'+str(i)])
    osc['plainParams'] = {'kParamEnable':0., 'kParamVolume':0.}
    put('Oscillator'+str(i), osc)
for i in range(3):
    put('RoutingSlot'+str(i), {'plainParams':{'kParamRoutingDest':'kRoutingDestFilter'}})
put('VoiceFilter0', {'plainParams':{'kParamEnable':1., 'kParamType':'B24',
    'kParamFreq':0.31, 'kParamReso':56., 'kParamDrive':24.,
    'kParamKeyTrack':0., 'kParamWet':100.}})
put('VoiceFilter1', {'plainParams':{'kParamEnable':0.}})
for i, (attack, hold, decay, sustain, release, curve) in enumerate([
    (0.0015,0.,0.44,0.,0.14,76.),
    (0.001,0.,0.18,0.,0.085,83.),
    (0.008,0.,0.68,0.,0.22,62.),
    (0.005,0.,2.,1.,0.075,66.6),
]):
    put('Env'+str(i), {'plainParams':{'kParamAttack':attack,'kParamHold':hold,
        'kParamDecay':decay,'kParamSustain':sustain,'kParamRelease':release,
        'kParamCurve1':50.,'kParamCurve2':curve,'kParamCurve3':70.}})

def lfo(i, points, curves, rate, mode):
    # JSON y is the drawn screen coordinate: 0 top, 1 bottom.
    put('LFO'+str(i), {'curveData':{'numPoints':len(points)-1,
        'xVals':[p[0] for p in points], 'yVals':[p[1] for p in points],
        'curveVals':curves}, 'curveDisplayName':'Neurospore '+str(i+1),
        'pathData':{}, 'plainParams':{'kParamBeatSync':0.,'kParamRate':rate,
        'kParamMode':mode,'kParamDefaultMode':0.,'kParamDotted':0.,'kParamTriplets':0.}})
lfo(0, [(0,1),(.035,0),(.18,.88),(.28,.17),(.49,.94),(.60,.35),(1,1)],
    [.5,.76,.5,.70,.5,.72,.5], 6.7, 'Envelope')
lfo(1, [(0,.85),(.18,.1),(.37,.68),(.55,0),(.78,.9),(1,.85)],
    [.62,.68,.55,.72,.5,.5], 2.3, 'Free')
lfo(2, [(0,0),(.08,1),(.12,0),(.23,1),(.31,.15),(.46,1),(.64,.4),(1,1)],
    [.68,.5,.68,.5,.72,.5,.76,.5], 14., 'Envelope')
lfo(3, [(0,.5),(.25,0),(.5,.5),(.75,1),(1,.5)],
    [.65,.35,.65,.35,.5], .17, 'Free')
for i in range(4,10):
    put('LFO'+str(i), {'curveData':{},'pathData':{},'plainParams':'default'})
for i in range(64):
    put('ModSlot'+str(i), {'plainParams':'default'})
routes = []
def route(source, module, index, param, amount, bipolar=False):
    reference = refs[module+':'+param]
    value = {'source':[source,0], 'destModuleTypeString':module,
        'destModuleID':index, 'destModuleParamName':param,
        'destModuleParamID':reference['destModuleParamID'],
        'plainParams':{'kParamAmount':amount,'kParamBipolar':float(bipolar),'kParamOut':100.}}
    put('ModSlot'+str(len(routes)),value)
    routes.append(value)
route(3,'VoiceFilter',0,'kParamFreq',36.)       # ENV 2 bite
route(6,'VoiceFilter',0,'kParamFreq',22.)       # LFO 1 double squelch
route(7,'WTOsc',0,'kParamTablePos',38.,True)    # LFO 2 vowel scan
route(8,'WTOsc',0,'kParamWarp',24.)            # LFO 3 FM rattle
route(9,'VoiceFilter',0,'kParamReso',9.,True)   # LFO 4 slow resonance
route(9,'WTOsc',2,'kParamTablePos',24.,True)   # LFO 4 metallic scan
route(4,'Oscillator',2,'kParamVolume',-12.)    # ENV 3 body changes
route(6,'Global',0,'kParamMasterTuning',2.,True)# LFO 1 small laser pitch bend
route(1,'VoiceFilter',0,'kParamFreq',12.)      # Wheel opens throat
route(1,'WTOsc',0,'kParamWarp',16.)           # Wheel adds FM

def effect(kind, number, params, **extra):
    return {'type':number,kind:{'plainParams':params},**extra}
put('FXRack0', {'displayName':'Neurospore Main','plainParams':'default','FX':[
    effect('FXDistortion',0,{'kParamEnable':1.,'kParamMode':'kOverdrive',
        'kParamDrive':46.,'kParamWet':62.},flex=[{},{}],kUIParamMixOrGain=0.),
    effect('FXPhaser',2,{'kParamEnable':1.,'kParamBeatSync':0.,'kParamRate':0.12,
        'kParamDepth':62.,'kParamDepth2':0.5,'kParamFeedback':42.,'kParamFreq':740.,
        'kParamNumPoles':6.,'kParamWidth':90.,'kParamWet':18.},lfophasor=0.,kUIParamMixOrGain=0.),
    effect('FXEQ',7,{'kParamEnable':1.,'kParamType1':2.,'kParamFreq1':180.,
        'kParamReso1':43.33,'kParamGain1':0.,'kParamType2':1.,'kParamFreq2':4100.,
        'kParamReso2':48.,'kParamGain2':1.5}),
    effect('FXDelay',4,{'kParamEnable':1.,'kParamBeatSync':0.,'kParamMode':1.,
        'kParamTimeL':(60/138)*.75,'kParamTimeR':(60/138)*.5,'kParamOffsetL':1.,
        'kParamOffsetR':1.,'kParamLink':0.,'kParamFeedback':33.,'kParamFreq':2800.,
        'kParamBW':2.6,'kParamWet':19.},kUIParamMixOrGain=0.),
    effect('FXReverb',6,{'kParamEnable':1.,'kParamType':'kPlate','kParamSize':28.,
        'kParamPreDelay':0.012,'kParamFreqB':50.,'kParamWet':13.,
        'kParamWidth':95.},kUIParamMixOrGain=0.),
]})
for i in (1,2):
    put('FXRack'+str(i),{'FX':[],'displayName':'','plainParams':'default'})
put('Global0', {'plainParams':{'kParamMasterVolume':0.44,'kParamPolyCount':6.,
    'kParamMonoToggle':0.,'kParamPortaAlways':0.,'kParamPortamentoTime':0.,
    'kParamLimitSameNotePolyphony':1.}})
# Init/default ARP and CLIP modules rather than inheriting the selected arp clip.
put('Arp0', {'plainParams':'default'})
put('ClipPlayer0', {'plainParams':'default'})
for section in ('metadata','data'):
    document[section]['presetName']='Psy - Neurospore'
    document[section]['presetAuthor']='Kaspe / Codex'
    document[section]['presetDescription']='Original Init-based psy FX. Embedded Formant Spine / FM Sine / Metallic Teeth; ENV bite, double squelch, FM rattle and slow drift. Wheel increases cutoff and FM. Experimental: load/readback/audition pending.'
    document[section]['tags']=['Wavetable','Embedded-Data','Poly']
output = ROOT / 'Psy_-_Neurospore.json'
output.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Neurospore_design_manifest.json').write_text(json.dumps({
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'changed_modules':list(dict.fromkeys(changes)),
    'modulation_routes':routes,
    'verification_pending':['Live load','wavetable names/frames','FM amount UI conversion',
        'WT position UI conversion','LFO curves/modes/rates','FX controls and output level','audition'],
    'mapping_reference':'https://github.com/btesser/serum2vital/blob/main/docs/FORMATS.md',
},indent=2),encoding='utf-8')
print(json.dumps({'output':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
    'table_samples':[t['numFrames'] for t in tables], 'modulation_routes':len(routes),
    'fx_count':len(d['FXRack0']['FX']),'changed_module_count':len(set(changes))}))
