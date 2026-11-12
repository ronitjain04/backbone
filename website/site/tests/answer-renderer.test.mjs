import {test} from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {renderAnswer} from '../answer-renderer.mjs';

function render(text){return renderAnswer(text,new JSDOM('').window.document)}

test('renders semantic Markdown instead of literal formatting markers',()=>{
 const el=render('## Addressability\n\n**Bits** per *location*.\n\n1. First\n2. Second\n\n> Check the source.\n\n| Type | Bits |\n| --- | --- |\n| Byte | 8 |');
 assert.equal(el.querySelector('h2').textContent,'Addressability');
 assert.equal(el.querySelector('strong').textContent,'Bits');
 assert.equal(el.querySelector('em').textContent,'location');
 assert.equal(el.querySelectorAll('ol li').length,2);
 assert.equal(el.querySelector('blockquote p').textContent,'Check the source.');
 assert.equal(el.querySelector('tbody td').textContent,'Byte');
});

test('highlights C and LC-3 without changing the original code',()=>{
 const c='int main(void) { return 0; }\n';
 const asm='.ORIG x3000\nADD R0, R1, #1 ; increment\nHALT\n.END\n';
 const el=render('```c\n'+c+'```\n\n```lc3\n'+asm+'```');
 const blocks=el.querySelectorAll('pre code');
 assert.equal(blocks[0].textContent,c);
 assert.equal(blocks[1].textContent,asm);
 assert.ok(blocks[0].querySelector('.hljs-keyword'));
 assert.ok(blocks[1].querySelector('.hljs-keyword'));
 assert.ok(blocks[1].querySelector('.hljs-comment'));
 assert.ok(blocks[1].querySelector('.hljs-built_in'));
});

test('unknown and malformed fence languages remain safe readable code',()=>{
 const el=render('```unknown\n<script>alert(1)</script>\n```\n\n```c" onmouseover="alert(1)\n<img src=x onerror=alert(1)>\n```');
 assert.equal(el.querySelectorAll('pre code').length,2);
 assert.equal(el.querySelector('pre code').textContent,'<script>alert(1)</script>\n');
 assert.equal(el.querySelector('script, img, [onmouseover]'),null);
});

test('inherited object property names are treated as unknown fence languages',()=>{
 for(const name of ['constructor','__proto__']){
  const el=render('```'+name+'\nint x = 1;\n```');
  assert.equal(el.querySelector('pre code').textContent,'int x = 1;\n');
  assert.equal(el.querySelector('.code-language').textContent,'Code');
 }
});

for(const [name,text] of [['dollar inline','$2^n$'],['dollar display','$$\n2^{16} \\times 16\n$$'],['bracket inline','\\(2^n\\)'],['bracket display','\\[\n\\frac{1}{2}\n\\]']]){
 test('renders '+name+' math with an accessible MathML representation',()=>{
  const el=render(text);
  assert.ok(el.querySelector('.katex'));
  assert.ok(el.querySelector('math'));
 });
}

test('leaves code literals and source-like citation text intact',()=>{
 const el=render('Use `struct Flight` [1].\n\n`$2^n$` and `\\(x\\)`.\n\n```c\nconst char *s = "\\\\[x\\\\]";\n```');
 assert.equal(el.querySelector('p code').textContent,'struct Flight');
 assert.equal(el.querySelectorAll('.katex').length,0);
 assert.ok(el.textContent.includes('[1]'));
});

test('malformed math remains visible and cannot inject markup',()=>{
 const el=render('$\\unknown{<img src=x onerror=alert(1)>}$');
 assert.ok(el.textContent.includes('unknown'));
 assert.equal(el.querySelector('img, script, [onerror]'),null);
});

test('blocks model HTML, dangerous links, remote images and trusted TeX commands',()=>{
 const el=render('<script>alert(1)</script><img src=x onerror=alert(1)>\n\n[bad](javascript:alert(1))\n\n![remote](https://example.com/tracker.png)\n\n$\\href{javascript:alert(1)}{bad}$\n\n$\\includegraphics{https://example.com/tracker.png}$');
 assert.equal(el.querySelector('script,img,iframe,object,[onerror]'),null);
 assert.equal(el.querySelector('a[href^="javascript:"]'),null);
});

test('preserves safe links with protections for a separate tab',()=>{
 const a=render('[Reference](https://example.com/reference)').querySelector('a');
 assert.equal(a.getAttribute('href'),'https://example.com/reference');
 assert.equal(a.getAttribute('target'),'_blank');
 assert.equal(a.getAttribute('rel'),'noopener noreferrer');
});
