import { ForecastResponse } from "../../types";
import { formatNumber } from "../../utils/formatters";

interface DataTableProps {
  data: ForecastResponse;
}

export function DataTable({ data }: DataTableProps) {
  const rows = data.series;
  const isDaily = rows.length > 0 && rows[0].time.length === 10;

  const handleDownload = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      "Time,Load,Temp,Humidity,Wind,Holiday\n" +
      rows
        .map(
          (e) =>
            `${e.time},${e.load},${e.temp ?? ""},${e.humidity ?? ""},${
              e.wind_speed ?? ""
            },${e.holiday ? "Yes" : "No"}`
        )
        .join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "forecast.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="table-wrap">
      <div className="table-action">
        <p>
          {rows.length} {isDaily ? "daily" : "hourly"} readings in this forecast
        </p>
        <button className="secondary" onClick={handleDownload}>
          ⇩ Download CSV
        </button>
      </div>
      <table>
        <thead>
          <tr>
            {["Date / Time", "Predicted Load (kW)", "Temperature (°C)", "Holiday"].map(
              (x) => (
                <th key={x}>{x}</th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{isDaily ? r.time : new Date(r.time).toLocaleString()}</td>
              <td>{formatNumber(r.load)}</td>
              <td>{r.temp !== null && r.temp !== undefined ? `${r.temp}°C` : "-"}</td>
              <td>
                {r.holiday ? (
                  <span className="no-pill amber">
                    {r.holiday_name || "Yes"}
                  </span>
                ) : (
                  <span className="no-pill">No</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
