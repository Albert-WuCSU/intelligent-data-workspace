import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import AgentProse,{inlineParts} from './AgentProse';
describe('safe conversational report prose',()=>{
 it('renders public headings lists emphasis and line breaks',()=>{
  const html=renderToStaticMarkup(<AgentProse text={'## 结果说明\n\n- **范围**：全部时间\n- 单位：`TEST`\n\n请核对口径。\n另行确认执行。'}/>);
  expect(html).toContain('<h3>结果说明</h3>');expect(html).toContain('<ul>');expect(html).toContain('<strong>范围</strong>');expect(html).toContain('<code>TEST</code>');expect(html).toContain('<br/>');
 });
 it('never enables HTML scripts links images or javascript',()=>{
  const html=renderToStaticMarkup(<AgentProse text={'<script>alert(1)</script>\n\n<img src=x onerror=alert(1)> [link](javascript:alert(1)) ![image](https://outside.invalid/data)'}/>);
  expect(html).not.toContain('<script>');expect(html).not.toContain('<img');expect(html).not.toContain('<a ');expect(html).toContain('&lt;script&gt;');
 });
 it('keeps unsupported or unmatched markup as plain text',()=>{
  expect(inlineParts('**incomplete')).toEqual([{kind:'text',text:'**incomplete'}]);expect(inlineParts('**ok**')[0]).toEqual({kind:'strong',text:'ok'});
 });
});
