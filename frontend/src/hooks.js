import { useEffect, useState } from "react";

// Runs loader(signal) whenever deps change; returns { data, error, loading }.
export function useApi(loader, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    const controller = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    loader(controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((err) => {
        if (err.name !== "AbortError") setState({ data: null, error: err.message, loading: false });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
