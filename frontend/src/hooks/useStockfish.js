import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Hook for client-side Stockfish WASM analysis via Web Worker.
 *
 * Returns:
 *   - engineReady: boolean -- whether the engine has initialized
 *   - engineFailed: boolean -- true if WASM failed to load (triggers fallback behavior)
 *   - getRefutation(fen, depth): Promise<string|null> -- returns UCI bestmove or null on failure
 *   - getEvaluation(fen, depth): Promise<{score: number, mate: number|null}|null> -- returns eval or null
 *   - getMultiPV(fen, numLines, depth): Promise<Array<{score, mate, pv: string[]}> | null> -- top N lines
 *   - stopAnalysis(): void -- cancel any in-flight multi-PV analysis
 */
export function useStockfish() {
  const workerRef = useRef(null);
  const [engineReady, setEngineReady] = useState(false);
  const [engineFailed, setEngineFailed] = useState(false);
  const pendingResolveRef = useRef(null);
  const timeoutRef = useRef(null);

  // Separate state for eval requests so they don't conflict with refutation
  const evalResolveRef = useRef(null);
  const evalTimeoutRef = useRef(null);
  const evalDataRef = useRef(null); // accumulates latest score info during search
  const activeRequestRef = useRef(null); // 'refutation' | 'eval' | 'multipv' | null

  // Multi-PV state
  const multiPvResolveRef = useRef(null);
  const multiPvTimeoutRef = useRef(null);
  const multiPvDataRef = useRef({}); // map of multipv index -> {score, mate, pv: [uci moves]}

  // Initialize engine on mount
  useEffect(() => {
    try {
      const worker = new Worker('/stockfish/stockfish-18-lite-single.js');
      workerRef.current = worker;

      worker.onmessage = (event) => {
        const line = typeof event.data === 'string' ? event.data : event.data?.data;
        if (!line) return;

        if (line === 'uciok') {
          worker.postMessage('isready');
        } else if (line === 'readyok') {
          setEngineReady(true);
        } else if (activeRequestRef.current === 'multipv' && line.startsWith('info depth')) {
          // Parse multi-PV info lines
          const pvIdxMatch = line.match(/multipv (\d+)/);
          if (!pvIdxMatch) return;
          const pvIdx = parseInt(pvIdxMatch[1], 10);

          const cpMatch = line.match(/score cp (-?\d+)/);
          const mateMatch = line.match(/score mate (-?\d+)/);
          let score = 0, mate = null;
          if (cpMatch) {
            score = parseInt(cpMatch[1], 10);
          } else if (mateMatch) {
            mate = parseInt(mateMatch[1], 10);
          }

          // Extract PV moves (everything after " pv ")
          const pvMatch = line.match(/ pv (.+)/);
          const pv = pvMatch ? pvMatch[1].split(' ') : [];

          multiPvDataRef.current[pvIdx] = { score, mate, pv };
        } else if (activeRequestRef.current === 'eval' && line.startsWith('info depth')) {
          // Parse score from info lines during eval request
          const cpMatch = line.match(/score cp (-?\d+)/);
          const mateMatch = line.match(/score mate (-?\d+)/);
          if (cpMatch) {
            evalDataRef.current = { score: parseInt(cpMatch[1], 10), mate: null };
          } else if (mateMatch) {
            evalDataRef.current = { score: 0, mate: parseInt(mateMatch[1], 10) };
          }
        } else if (line.startsWith('bestmove')) {
          if (activeRequestRef.current === 'multipv') {
            // Multi-PV request complete
            clearTimeout(multiPvTimeoutRef.current);
            // Reset MultiPV to 1
            try { worker.postMessage('setoption name MultiPV value 1'); } catch (e) { /* */ }
            if (multiPvResolveRef.current) {
              // Convert map to sorted array
              const data = multiPvDataRef.current;
              const lines = Object.keys(data)
                .sort((a, b) => parseInt(a) - parseInt(b))
                .map(k => data[k]);
              multiPvResolveRef.current(lines.length > 0 ? lines : null);
              multiPvResolveRef.current = null;
            }
            activeRequestRef.current = null;
          } else if (activeRequestRef.current === 'eval') {
            // Eval request complete
            clearTimeout(evalTimeoutRef.current);
            if (evalResolveRef.current) {
              evalResolveRef.current(evalDataRef.current || { score: 0, mate: null });
              evalResolveRef.current = null;
            }
            activeRequestRef.current = null;
          } else {
            // Refutation request complete
            const bestmove = line.split(' ')[1];
            if (pendingResolveRef.current) {
              clearTimeout(timeoutRef.current);
              pendingResolveRef.current(bestmove || null);
              pendingResolveRef.current = null;
            }
            activeRequestRef.current = null;
          }
        }
      };

      worker.onerror = () => {
        setEngineFailed(true);
      };

      worker.postMessage('uci');
    } catch (e) {
      console.error('Stockfish WASM failed to load:', e);
      setEngineFailed(true);
    }

    return () => {
      if (workerRef.current) {
        try {
          workerRef.current.postMessage('quit');
          workerRef.current.terminate();
        } catch (e) {
          // Worker already terminated
        }
        workerRef.current = null;
      }
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (evalTimeoutRef.current) {
        clearTimeout(evalTimeoutRef.current);
      }
      if (multiPvTimeoutRef.current) {
        clearTimeout(multiPvTimeoutRef.current);
      }
    };
  }, []);

  const cancelAll = useCallback(() => {
    if (pendingResolveRef.current) {
      pendingResolveRef.current(null);
      pendingResolveRef.current = null;
    }
    if (evalResolveRef.current) {
      evalResolveRef.current(null);
      evalResolveRef.current = null;
    }
    if (multiPvResolveRef.current) {
      multiPvResolveRef.current(null);
      multiPvResolveRef.current = null;
    }
  }, []);

  const getRefutation = useCallback((fen, depth = 15) => {
    return new Promise((resolve) => {
      if (!workerRef.current || !engineReady || engineFailed) {
        resolve(null);
        return;
      }

      cancelAll();

      pendingResolveRef.current = resolve;
      activeRequestRef.current = 'refutation';

      // Timeout after 3 seconds -- graceful fallback
      timeoutRef.current = setTimeout(() => {
        if (pendingResolveRef.current) {
          try {
            workerRef.current.postMessage('stop');
          } catch (e) {
            // Worker already terminated
          }
          pendingResolveRef.current(null);
          pendingResolveRef.current = null;
          activeRequestRef.current = null;
        }
      }, 3000);

      try {
        workerRef.current.postMessage(`position fen ${fen}`);
        workerRef.current.postMessage(`go depth ${depth}`);
      } catch (e) {
        console.error('Error sending message to Stockfish worker:', e);
        resolve(null);
      }
    });
  }, [engineReady, engineFailed, cancelAll]);

  const getEvaluation = useCallback((fen, depth = 18) => {
    return new Promise((resolve) => {
      if (!workerRef.current || !engineReady || engineFailed) {
        resolve(null);
        return;
      }

      cancelAll();

      evalResolveRef.current = resolve;
      evalDataRef.current = null;
      activeRequestRef.current = 'eval';

      // Timeout after 5 seconds
      evalTimeoutRef.current = setTimeout(() => {
        if (evalResolveRef.current) {
          try {
            workerRef.current.postMessage('stop');
          } catch (e) {
            // Worker already terminated
          }
          // Return whatever we have so far
          evalResolveRef.current(evalDataRef.current || null);
          evalResolveRef.current = null;
          activeRequestRef.current = null;
        }
      }, 5000);

      try {
        workerRef.current.postMessage(`position fen ${fen}`);
        workerRef.current.postMessage(`go depth ${depth}`);
      } catch (e) {
        console.error('Error sending message to Stockfish worker:', e);
        resolve(null);
      }
    });
  }, [engineReady, engineFailed, cancelAll]);

  const getMultiPV = useCallback((fen, numLines = 3, depth = 20) => {
    return new Promise((resolve) => {
      if (!workerRef.current || !engineReady || engineFailed) {
        resolve(null);
        return;
      }

      cancelAll();

      multiPvResolveRef.current = resolve;
      multiPvDataRef.current = {};
      activeRequestRef.current = 'multipv';

      // Timeout after 8 seconds
      multiPvTimeoutRef.current = setTimeout(() => {
        if (multiPvResolveRef.current) {
          try {
            workerRef.current.postMessage('stop');
          } catch (e) {
            // Worker already terminated
          }
          // Reset MultiPV
          try { workerRef.current.postMessage('setoption name MultiPV value 1'); } catch (e) { /* */ }
          // Return whatever we have so far
          const data = multiPvDataRef.current;
          const lines = Object.keys(data)
            .sort((a, b) => parseInt(a) - parseInt(b))
            .map(k => data[k]);
          multiPvResolveRef.current(lines.length > 0 ? lines : null);
          multiPvResolveRef.current = null;
          activeRequestRef.current = null;
        }
      }, 8000);

      try {
        workerRef.current.postMessage(`setoption name MultiPV value ${numLines}`);
        workerRef.current.postMessage(`position fen ${fen}`);
        workerRef.current.postMessage(`go depth ${depth}`);
      } catch (e) {
        console.error('Error sending message to Stockfish worker:', e);
        resolve(null);
      }
    });
  }, [engineReady, engineFailed, cancelAll]);

  const stopAnalysis = useCallback(() => {
    if (!workerRef.current) return;
    try {
      workerRef.current.postMessage('stop');
    } catch (e) {
      // Worker already terminated
    }
    if (multiPvResolveRef.current) {
      clearTimeout(multiPvTimeoutRef.current);
      try { workerRef.current.postMessage('setoption name MultiPV value 1'); } catch (e) { /* */ }
      multiPvResolveRef.current(null);
      multiPvResolveRef.current = null;
      if (activeRequestRef.current === 'multipv') {
        activeRequestRef.current = null;
      }
    }
  }, []);

  return { engineReady, engineFailed, getRefutation, getEvaluation, getMultiPV, stopAnalysis };
}
