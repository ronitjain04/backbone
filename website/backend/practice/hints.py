"""Reviewed hint ladders anchored to the existing private-course retriever."""
from .bank import fingerprint
from .checking import verdict


def grounded_chunks(exercise,retriever,query=''):
    if retriever is None:return []
    available={(c['source'],c.get('details',''),fingerprint(c)):c for c in retriever.chunks}
    anchors=[]
    for ref in exercise['references']:
        chunk=available.get((ref['source'],ref['details'],ref['fingerprint']))
        if chunk is None:return []
        anchors.append(chunk)
    retrieved=retriever.search(exercise['prompt']+' '+query)
    unique={}
    for chunk in anchors+retrieved:
        unique.setdefault((chunk['source'],chunk.get('details',''),fingerprint(chunk)),chunk)
    return list(unique.values())[:6]


def make_hint(exercise,level,attempts,retriever):
    level=max(1,min(3,level))
    previous=[a for a in attempts if a.get('result') and a['result'].get('misconception')]
    misconception=previous[-1]['result']['misconception'] if previous else None
    query=' '.join(r['description'] for r in exercise['rubric'])
    if misconception:query+=' '+misconception['label']
    chunks=grounded_chunks(exercise,retriever,query)
    if not chunks:return verdict('unavailable','I cannot verify the supporting material for this hint right now. Your work is saved.')
    message=exercise['hints'][level-1]
    if level>1 and misconception:
        message+='\n\nRevisit this step from your earlier work: “'+misconception['evidence']+'”. How does the cited rule apply here?'
    previous_hints=[a for a in attempts if a.get('result',{}) and a['result'].get('status')=='hint']
    if level==3 and any(a['result'].get('level')==3 for a in previous_hints):
        message='Try applying the last step to a fresh attempt. '+message
    # Reviewed text supplies the scaffold; the retriever supplies verifiable evidence.
    return verdict('hint',message+' [1]',level=level,sources=[dict(c,citation_id=i,fingerprint=fingerprint(c)) for i,c in enumerate(chunks,1)],hint_version='reviewed-ladder-1')
