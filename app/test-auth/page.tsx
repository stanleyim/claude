'use client'

import { supabase } from '@/lib/supabase'
import { useState } from 'react'

export default function TestAuthPage() {
  const [result, setResult] = useState('')

  const handleTest = async () => {
    const { data, error } = await supabase.auth.signUp({
      email: 'imroetaeck@gmail.com',
      password: 'test1234'
    })
    setResult(error ? error.message : '이메일 발송 성공! Gmail 확인해봐')
  }

  return (
    <div className="p-8">
      <button onClick={handleTest} className="bg-blue-500 text-white px-4 py-2 rounded">
        테스트 이메일 보내기
      </button>
      <p className="mt-4">{result}</p>
    </div>
  )
}
