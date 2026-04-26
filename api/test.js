export const runtime = 'nodejs';

export default function handler(req, res) {
  try {
    return res.status(200).json({
      ok: true,
      message: "API working",
      time: new Date().toISOString()
    });
  } catch (error) {
    return res.status(500).json({
      ok: false,
      error: error.message
    });
  }
}
