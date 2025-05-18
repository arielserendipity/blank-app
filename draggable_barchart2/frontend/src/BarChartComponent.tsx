import {
  Streamlit,
  withStreamlitConnection,
  ComponentProps,
} from "streamlit-component-lib"
import React, { useCallback, useEffect, useMemo, useState, ReactElement } from "react"

// Debounce utility
function debounce<T extends (...args: any[]) => void>(func: T, wait = 2000): T {
  let timeout: ReturnType<typeof setTimeout>;
  return ((...args: any[]) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  }) as T;
}

// Debounced version of Streamlit.setComponentValue with 2s delay
const debouncedSetComponentValue = debounce(Streamlit.setComponentValue, 500);

function Bar({ value, onValueChange, targetAverage, label, showHint }: { value: number; onValueChange: (value: number) => void; targetAverage: number; label?: string; showHint?: boolean }) {
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const updateValueFromEvent = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const offsetY = e.clientY - rect.top;
    const pct = 1 - offsetY / rect.height;
    const newValue = Math.round(Math.max(0, Math.min(1, pct)) * 10);
    onValueChange(newValue);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    setIsDragging(true);
    updateValueFromEvent(e);
  }, [updateValueFromEvent]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    updateValueFromEvent(e);
  }, [isDragging, updateValueFromEvent]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, [value]);


  return (
    <div
      className="stBlock"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      style={{
        position: 'relative',
        width: '5rem',
        height: '20rem',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'end',
        alignItems: 'center',
      }}
    >
      <div style={{
        width: '3rem',
        height: `${value * 10}%`,
        backgroundColor: '#9551ef',
        boxShadow: `0 0 10px rgba(128, 128, 128, 0.3)`,
        borderRadius: '2px 2px 0 0',
      }} />
      {showHint && (targetAverage - value * 10 > 0 ?
        <div style={{
          position: 'absolute',
          width: '3rem',
          height: `${targetAverage - value * 10}%`,
          bottom: `${value * 10}%`,
          backgroundColor: (targetAverage - value * 10>0)?'#95ef51':'#9551ef',
          boxShadow: `0 0 10px rgba(128, 128, 128, 0.3)`,
          borderRadius: '2px 2px 0 0',
        }} />
        :
        <div style={{
          position: 'absolute',
          width: '3rem',
          height: `${value * 10 - targetAverage}%`,
          bottom: `${targetAverage}%`,
          backgroundColor: (targetAverage - value * 10>0)?'#95ef51':'#9551ef',
          boxShadow: `0 0 10px rgba(128, 128, 128, 0.3)`,
          borderRadius: '2px 2px 0 0',
        }} />
      )}
      <div style={{
        position: 'absolute',
        width: '3rem',
        top: `${93 - value * 10}%`,
        pointerEvents: 'none',
        userSelect: 'none',
        textAlign: 'center',
        fontSize: '0.85rem',
      }}>
        {value}
      </div>
      {label && (
        <div
          style={{
            position: "absolute",
            bottom: "-1.5rem",
            width: "100%",
            textAlign: "center",
            fontSize: "0.85rem",
            color: "#444",
            userSelect: "none",
            pointerEvents: "none",
          }}
        >
          {label}
        </div>
      )}
    </div>
  )
}

function BarChartComponent({ args, disabled, theme }: ComponentProps): ReactElement {
  // 1) Initialize five values from args.values or default to [0,0,0,0,0]
  const [values, setValues] = useState<number[]>(() => {
    const argVals = args.values as number[] | undefined;
    return Array.isArray(argVals) && argVals.length === 5
      ? argVals
      : [6, 6, 6, 6, 6];
  });
  const hint = (args.hint || false) as boolean;

  // 2) Resize frame when theme or values change
  useEffect(() => {
    Streamlit.setFrameHeight();
  }, [theme, values]);

  const targetAverage = 60;

  // 3) Handler to update a single bar and send back to Streamlit
  const handleValueChange = (index: number) => (newValue: number) => {
    setValues((prevValues) => {
      const newValues = [...prevValues];
      newValues[index] = newValue;

      // // get list of indices sorted by value
      // const sortedIndices = Array.from(Array(newValues.length).keys()).sort((a, b) => newValues[a] - newValues[b]);
      // // move 'index' to the end of the sorted list
      // sortedIndices.splice(sortedIndices.indexOf(index), 1);

      // const targetSum = targetAverage * newValues.length;
      // const currentSum = newValues.reduce((acc, val) => acc + val, 0);
      // let diff = targetSum - currentSum;
      // if (diff > 0) {
      //   for (let adjustIndex of sortedIndices.concat(index)) {
      //     const increment = Math.min(diff, 100 - newValues[adjustIndex]);
      //     newValues[adjustIndex] += increment;
      //     diff -= increment;
      //     }
      // } else {
      //   for (let adjustIndex of sortedIndices.reverse().concat(index)) {
      //     const decrement = Math.min(-diff, newValues[adjustIndex]);
      //     newValues[adjustIndex] -= decrement;
      //     diff += decrement;
      //   }
      // }

      debouncedSetComponentValue(newValues);
      return newValues;
    });
  };

  const currentAverage = useMemo(() => {
    const sum = values.reduce((acc, val) => acc + val, 0);
    return (sum / values.length);
  }, [values]);

  // 4) Render five Bar components side by side
  return (
    <div style={{
      display: "flex",
      width: "fit-content",
      gap: "1rem",
      justifyContent: "center",
      boxShadow: `inset 0 -10px 10px -10px rgba(128, 128, 128, 0.2), inset 0 10px 10px -10px rgba(128, 128, 128, 0.1)`,
      paddingTop: "1.5rem",
      paddingBottom: "3.5rem",
      userSelect: "none",
    }}>
      <div style={{
        position: "relative",
        height: "20rem",
        marginLeft: "1.5rem",
        backgroundColor: "#d0d0d0",
        width: "1px",
        display: "flex",
        flexDirection: "column",
        alignItems: "start",
      }}>
        {
          Array.from({ length: 11 }, (_, i) => (
            <div key={i} style={{
              position: "absolute",
              width: "32rem",
              height: "1px",
              top: `${i * 10}%`,
              opacity: 0.5,
              fontSize: "0.7rem",
              backgroundColor: "#e0e0e0",
              display: "flex",
              alignItems: "flex-end",
            }}>
              <div style={{
                width: "1.2rem",
                marginLeft: "-1.4rem",
                textAlign: "right",
              }}>
                {10 - i}
              </div>
            </div>
          ))
        }
        <div style={{
          position: "absolute",
          width: "32rem",
          height: "1px",
          top: `${(100 - currentAverage * 10)}%`,
          fontSize: "0.7rem",
          borderTop: "1px dashed #f57030",
          color: "#f57030",
          display: "flex",
          alignItems: "flex-end",
          paddingLeft: "0.2rem",
        }}>
          현재 평균
        </div>
      </div>
      {values.map((val, idx) => (
        <Bar
          key={idx}
          value={val}
          targetAverage={targetAverage}
          showHint={hint}
          label={args.labels ? args.labels[idx] : undefined}
          onValueChange={handleValueChange(idx)}
        />
      ))}
    </div>
  );
}

// "withStreamlitConnection" is a wrapper function. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).
export default withStreamlitConnection(BarChartComponent)
