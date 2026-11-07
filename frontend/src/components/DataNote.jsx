import { getHealth } from "../api";
import { useApi } from "../hooks";
import { formatDate, monthLabel } from "../format";

// Says how fresh the data is, so nobody mistakes an old snapshot for live numbers.
export default function DataNote() {
  const { data: meta } = useApi((signal) => getHealth(signal), []);
  if (!meta || !meta.data_through) return null;
  const t = meta.data_through;
  return (
    <span>
      Data snapshot: matches to {formatDate(t.matches)}, Transfermarkt values to {formatDate(t.valuations)}, transfers
      mostly to {monthLabel(t.transfers)}.{" "}
      {meta.live_as_of
        ? `Current-season statistics updated ${formatDate(meta.live_as_of)}.`
        : "Current-season statistics have not been loaded yet."}
    </span>
  );
}
