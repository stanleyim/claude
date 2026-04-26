export default function handler(req, res) {
  res.status(200).json({
    top10: ["AAPL", "TSLA", "MSFT"],
    signal: "BUY"
  });
}
