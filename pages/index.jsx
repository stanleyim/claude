import { useEffect, useState } from 'react'

export default function Home() {
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/test')
      .then(res => {
        if (!res.ok) throw new Error(`API ${res.status} 에러`)
        return res.json()
      })
      .then(setReport)
      .catch(setError)
  }, [])

  if (error) return <p style={{padding: '40px', color: 'red'}}>에러: {error.message}</p>
  if (!report) return <p style={{padding: '40px'}}>Loading...</p>

  return (
    <div style={{ padding: '40px', fontFamily: 'system-ui', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '32px', marginBottom: '8px', fontWeight: '700' }}>{report.title}</h1>
      <p style={{ color: '#666', marginBottom: '32px' }}>{report.summary}</p>
      
      <div style={{ display: 'grid', gap: '12px' }}>
        {report.data.map(item => (
          <div 
            key={item.code} 
            style={{ 
              border: '1px solid #e5e5e5', 
              borderRadius: '12px', 
              padding: '20px',
              background: '#fff'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div>
                <span style={{ 
                  background: '#f3f3f3', 
                  padding: '4px 10px', 
                  borderRadius: '6px', 
                  fontSize: '12px',
                  marginRight: '8px'
                }}>
                  #{item.rank}
                </span>
                <strong style={{ fontSize: '18px' }}>{item.name}</strong>
                <span style={{ color: '#888', marginLeft: '8px', fontSize: '14px' }}>{item.code}</span>
              </div>
              <div style={{ 
                color: item.result === 'hit' ? '#10b981' : '#ef4444',
                fontWeight: '600'
              }}>
                {item.result === 'hit' ? '적중' : '미적중'} 
                <span style={{ marginLeft: '8px' }}>
                  {item.finalReturn > 0 ? '+' : ''}{item.finalReturn.toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
              진입가: {item.entryPrice.toLocaleString()}원 | 점수: {item.score}점 | 진입일: {item.entryDate}
            </div>
            
            <div style={{ fontSize: '13px', color: '#888' }}>
              {item.reasons.join(' · ')}
            </div>
            
            <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>
              리스크: {item.risk}
            </div>
          </div>
        ))}
      </div>
      
      <p style={{ color: '#999', fontSize: '12px', marginTop: '32px' }}>
        생성시간: {new Date(report.generatedAt).toLocaleString('ko-KR')}
      </p>
    </div>
  )
}
