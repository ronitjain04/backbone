"""Reviewed contrasting example; never substitutes an exercise's expected answer."""
SUPPORTED={'mem-03','mem-06','mem-03-follow','mem-06-follow'}
STAGES=(
 'Which describes the number of locations, and which describes the bits stored at each location? Change one quantity at a time.',
 'Each address selects one location. With a address bits there are 2^a locations. Addressability tells you how many bits fit in each location.',
 'Multiply locations by bits per location to obtain total bits. Divide total bits by 8 to express the same capacity in bytes. Check the units at each step.'
)

def explanation(exercise,stage,attempts,chunks):
    if exercise['id'] not in SUPPORTED:raise KeyError('No visual for this exercise')
    if not chunks:return {'status':'unavailable','message':'The visual’s supporting sources cannot be verified right now. Your work is saved.'}
    evidence=None
    for attempt in reversed(attempts):
        if attempt.get('kind')!='check':continue
        result=attempt.get('result') or {}
        if result.get('status')=='correct':break
        finding=result.get('misconception')
        text=attempt.get('input',{}).get('work','')
        if finding and finding.get('evidence') and finding['evidence'] in text:
            evidence=finding;break
    return {'status':'visual','stage':stage,'message':STAGES[stage-1],
            'evidence':evidence,'clarification':None if evidence else 'In your own calculation, which quantity counts locations and which describes one location?',
            'sources':chunks,'visual_version':'memory-addressability-1',
            'example_note':'A contrasting example. The starting values are not taken from your exercise.'}
