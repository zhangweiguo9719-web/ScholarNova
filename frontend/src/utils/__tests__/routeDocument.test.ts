import { describe, expect, it } from 'vitest'
import { buildRouteDocumentHtml } from '../routeDocument'

const origin = 'http://127.0.0.1:5173'
const route = { title: '研究路线', status: 'active', description: '', ai_analysis: '' }
const parse = (html: string) => new DOMParser().parseFromString(html, 'text/html')

describe('research route document export', () => {
  it('renders untrusted titles, status, text and model labels as text, not active HTML', () => {
    const title = '</title><script>window.pwned = true</script><h1>Injected</h1>'
    const malicious = '<img src=x onerror="window.pwned=true"> & <svg onload="window.pwned=true">'
    const html = buildRouteDocumentHtml({
      title,
      status: malicious,
      description: malicious,
      ai_analysis: `## 文字分析（${malicious}）\n${malicious}\n## 研究架构图（${malicious}）\n${malicious}`,
    }, origin)
    const doc = parse(html)
    expect(doc.title).toBe(title)
    expect(doc.querySelector('h1')?.textContent).toBe(title)
    expect(doc.querySelectorAll('h1')).toHaveLength(1)
    expect(doc.querySelectorAll('script, img, svg, iframe, object')).toHaveLength(0)
    expect(doc.body.textContent).toContain(malicious)
    expect([...doc.querySelectorAll('span')].every((span) => span.textContent?.includes(malicious))).toBe(true)
  })

  it('blocks non-web image schemes and prevents image-attribute injection', () => {
    const doc = parse(buildRouteDocumentHtml({
      ...route,
      ai_analysis: [
        '![bad](javascript:alert(1))',
        '![bad](data:image/svg+xml;base64,AAAA)',
        '![bad](file:///etc/passwd)',
        '![bad](//other.example/image.png)',
        '![bad](/\\other.example/image.png)',
        '![quote](https://images.example/figure.png" onerror="window.pwned=true)',
      ].join('\n'),
    }, origin))
    const images = doc.querySelectorAll('img')
    expect(images).toHaveLength(1)
    expect(images[0].getAttribute('src')).toContain('https://images.example/figure.png%22')
    expect(images[0].hasAttribute('onerror')).toBe(false)
    expect([...doc.querySelectorAll('*')].flatMap((el) => [...el.attributes])
      .some((attr) => attr.name.startsWith('on'))).toBe(false)
  })

  it('preserves paragraphs, model names and local / HTTP(S) figure URLs', () => {
    const doc = parse(buildRouteDocumentHtml({
      ...route,
      title: 'A & B <研究>',
      description: '**目标**\n第二阶段',
      ai_analysis: '## 文字分析（zhipu/glm-5.2）\n比较 A & B\n## 研究架构图（sensenova/u1）\n说明\n![本地图](/generated/route.png)\n![远程图](https://images.example/route.png?a=1&b=2)\n![HTTP图](http://images.example/route.png)',
    }, origin))
    expect(doc.title).toBe('A & B <研究>')
    const paragraphTexts = [...doc.querySelectorAll('p')].map((p) => p.textContent)
    expect(paragraphTexts).toContain('目标')
    expect(paragraphTexts).toContain('第二阶段')
    expect(paragraphTexts).toContain('比较 A & B')
    expect(doc.body.textContent).toContain('文字分析：zhipu/glm-5.2')
    expect(doc.body.textContent).toContain('架构图：sensenova/u1')
    expect([...doc.querySelectorAll('img')].map((img) => img.getAttribute('src'))).toEqual([
      `${origin}/generated/route.png`,
      'https://images.example/route.png?a=1&b=2',
      'http://images.example/route.png',
    ])
  })
})
