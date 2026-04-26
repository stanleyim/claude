import fs from 'fs'
import path from 'path'

export default function handler(req, res) {
  try {
    const filePath = path.join(process.cwd(), 'data', 'report.json')
    const fileContents = fs.readFileSync(filePath, 'utf8')
    const data = JSON.parse(fileContents)
    res.status(200).json(data)
  } catch (e) {
    res.status(500).json({ error: e.message })
  }
}
