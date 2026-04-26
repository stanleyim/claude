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
    <div style={{ padding: '40px', fontFamily: 'system-ui' }}>
      <h1 style={{ fontSize: '28px', marginBottom: '8px' }}>{report.title}</h1>
      <p style={{ color: '#666', marginBottom: '24px' }}>{report.summary}</p>
      <div style={{ border: '1px solid #eee', borderRadius: '8px', padding: '16px' }}>
        {report.data.length === 0 ? (
          <p>데이터 없음</p>
        ) : (
          report.data.map(item => (
            <div key={item.date} style={{ padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
              <strong>{item.date}</strong> - {item.users}명
            </div>
          ))
        )}
      </div>
    </div>
  )
                        }
