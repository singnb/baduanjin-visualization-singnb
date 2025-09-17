// src/components/Charts/JointAngleChart.js

import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { loadMasterData, loadLearnerData } from '../../services/dataLoader';
import './JointAngleChart.css';

function JointAngleChart({ comparisonMode = 'sideBySide', compact = false }) {
  const [masterData, setMasterData] = useState(null);
  const [learnerData, setLearnerData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Selected joints to display
  const [selectedJoints, setSelectedJoints] = useState([
    'elbow', 
    'shoulder', 
    'hip'
  ]);
  
  // Focus range for frames
  const [focusRange, setFocusRange] = useState([0, 1200]);
  
  // Height per plot (new state)
  const [heightPerPlot, setHeightPerPlot] = useState(240);
  
  // Problem areas detection
  const [problemAreas, setProblemAreas] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        console.log("Fetching joint angle data using dataLoader...");
        
        // Load master data using the dataLoader service
        const masterResult = await loadMasterData('jointAngles');
        console.log("Master data loaded:", masterResult);
        setMasterData(masterResult);
        
        // Load learner data using the dataLoader service
        const learnerResult = await loadLearnerData('jointAngles');
        console.log("Learner data loaded:", learnerResult);
        setLearnerData(learnerResult);
        
        setLoading(false);
      } catch (err) {
        console.error('Error loading joint angle data:', err);
        setError('Failed to load joint angle data. Please try again later.');
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  // Calculate problem areas when data changes
  useEffect(() => {
    if (masterData && learnerData) {
      const areas = [];
      
      selectedJoints.forEach(joint => {
        // Handle regular joints (with left/right)
        if (['elbow', 'shoulder', 'hip', 'knee'].includes(joint)) {
          ['left', 'right'].forEach(side => {
            const fullJoint = `${side}_${joint}`;
            
            if (masterData.angles && masterData.angles[fullJoint] && 
                learnerData.angles && learnerData.angles[fullJoint]) {
              
              // Find frames where difference is significant (more than 15 degrees)
              let inProblemArea = false;
              let startFrame = 0;
              let maxDiff = 0;
              
              // Get interpolated data across all frames in the focus range
              const masterInterpolated = interpolateKeyPoseData(masterData, fullJoint, focusRange[1]);
              const learnerInterpolated = interpolateKeyPoseData(learnerData, fullJoint, focusRange[1]);
              
              for (let i = 0; i < masterInterpolated.length; i++) {
                const diff = Math.abs(masterInterpolated[i] - learnerInterpolated[i]);
                
                if (diff > 15 && !inProblemArea) {
                  // Start of a problem area
                  inProblemArea = true;
                  startFrame = i;
                  maxDiff = diff;
                } else if (diff > 15 && inProblemArea) {
                  // Continue problem area
                  maxDiff = Math.max(maxDiff, diff);
                } else if (diff <= 15 && inProblemArea) {
                  // End of a problem area - add padding for smoother visualization
                  const paddedStart = Math.max(0, startFrame - 2);
                  const paddedEnd = Math.min(masterInterpolated.length - 1, i + 2);
                  
                  areas.push({
                    joint: fullJoint,
                    frames: [paddedStart, paddedEnd],
                    diff: maxDiff.toFixed(1)
                  });
                  
                  inProblemArea = false;
                }
              }
              
              // If we're still in a problem area at the end of the data
              if (inProblemArea) {
                const paddedStart = Math.max(0, startFrame - 2);
                const paddedEnd = masterInterpolated.length - 1;
                
                areas.push({
                  joint: fullJoint,
                  frames: [paddedStart, paddedEnd],
                  diff: maxDiff.toFixed(1)
                });
              }
            }
          });
        } 
        // Handle spine_top and spine_bottom directly
        else if (joint === 'spine_top' || joint === 'spine_bottom') {
          if (masterData.angles && masterData.angles[joint] && 
              learnerData.angles && learnerData.angles[joint]) {
            
            // Find frames where difference is significant (more than 15 degrees)
            let inProblemArea = false;
            let startFrame = 0;
            let maxDiff = 0;
            
            // Get interpolated data across all frames in the focus range
            const masterInterpolated = interpolateKeyPoseData(masterData, joint, focusRange[1]);
            const learnerInterpolated = interpolateKeyPoseData(learnerData, joint, focusRange[1]);
            
            for (let i = 0; i < masterInterpolated.length; i++) {
              const diff = Math.abs(masterInterpolated[i] - learnerInterpolated[i]);
              
              if (diff > 15 && !inProblemArea) {
                // Start of a problem area
                inProblemArea = true;
                startFrame = i;
                maxDiff = diff;
              } else if (diff > 15 && inProblemArea) {
                // Continue problem area
                maxDiff = Math.max(maxDiff, diff);
              } else if (diff <= 15 && inProblemArea) {
                // End of a problem area - add padding for smoother visualization
                const paddedStart = Math.max(0, startFrame - 2);
                const paddedEnd = Math.min(masterInterpolated.length - 1, i + 2);
                
                areas.push({
                  joint,
                  frames: [paddedStart, paddedEnd],
                  diff: maxDiff.toFixed(1)
                });
                
                inProblemArea = false;
              }
            }
            
            // If we're still in a problem area at the end of the data
            if (inProblemArea) {
              const paddedStart = Math.max(0, startFrame - 2);
              const paddedEnd = masterInterpolated.length - 1;
              
              areas.push({
                joint,
                frames: [paddedStart, paddedEnd],
                diff: maxDiff.toFixed(1)
              });
            }
          }
        }
      });
      
      setProblemAreas(areas);
    }
  }, [masterData, learnerData, selectedJoints, focusRange]);
  
  // Function to interpolate data between key pose frames
  const interpolateKeyPoseData = (data, joint, maxFrame) => {
    const result = new Array(maxFrame + 1).fill(0);
    
    // If data is missing or joint doesn't exist, return zero array
    if (!data || !data.angles || !data.angles[joint]) {
      return result;
    }
    
    // If the data comes in frame/value format
    if (data.frames && Array.isArray(data.frames)) {
      const frames = data.frames;
      const values = data.angles[joint];
      
      // For each point in the result array
      for (let i = 0; i <= maxFrame; i++) {
        // Find the closest frames
        let beforeIdx = -1;
        let afterIdx = -1;
        
        for (let j = 0; j < frames.length; j++) {
          if (frames[j] <= i) {
            beforeIdx = j;
          }
          if (frames[j] >= i && afterIdx === -1) {
            afterIdx = j;
          }
        }
        
        // Different cases for interpolation
        if (beforeIdx === -1) {
          // Before the first frame, use the first value
          result[i] = values[0] || 0;
        } else if (afterIdx === -1 || afterIdx === beforeIdx) {
          // After the last frame, use the last value
          result[i] = values[beforeIdx] || 0;
        } else {
          // Interpolate between two frames
          const beforeFrame = frames[beforeIdx];
          const afterFrame = frames[afterIdx];
          const beforeValue = values[beforeIdx] || 0;
          const afterValue = values[afterIdx] || 0;
          
          // Linear interpolation
          const ratio = (i - beforeFrame) / (afterFrame - beforeFrame);
          result[i] = beforeValue + ratio * (afterValue - beforeValue);
        }
      }
      return result;
    }
    
    // If the data comes in key pose format with keyPoseFrames and angles
    if (data.keyPoseFrames && data.angles[joint]) {
      const frames = data.keyPoseFrames;
      const angles = data.angles[joint];
      
      // For each point in the result array
      for (let i = 0; i <= maxFrame; i++) {
        // Find the closest key pose frames
        let before = -1;
        let after = -1;
        
        for (let j = 0; j < frames.length; j++) {
          if (frames[j] <= i) {
            before = j;
          }
          if (frames[j] >= i && after === -1) {
            after = j;
          }
        }
        
        // Different cases for interpolation
        if (before === -1) {
          // Before the first key pose, use the first value
          result[i] = angles[0] || 0;
        } else if (after === -1 || after === before) {
          // After the last key pose, use the last value
          result[i] = angles[before] || 0;
        } else {
          // Interpolate between two key poses
          const beforeFrame = frames[before];
          const afterFrame = frames[after];
          const beforeAngle = angles[before] || 0;
          const afterAngle = angles[after] || 0;
          
          // Linear interpolation
          const ratio = (i - beforeFrame) / (afterFrame - beforeFrame);
          result[i] = beforeAngle + ratio * (afterAngle - beforeAngle);
        }
      }
      return result;
    }
    
    return result;
  };
  
  if (loading) {
    return <div className="loading">Loading joint angle data...</div>;
  }
  
  if (error) {
    return <div className="error">{error}</div>;
  }
  
  if (!masterData || !learnerData) {
    return <div className="error">No joint angle data available</div>;
  }
  
  // Extract available joints from data
  const getAvailableJoints = () => {
    const joints = new Set();
    
    if (masterData && masterData.angles) {
      Object.keys(masterData.angles).forEach(joint => {
        if (joint === 'spine_top' || joint === 'spine_bottom') {
          // Keep spine_top and spine_bottom as is
          joints.add(joint);
        } else {
          // Extract joint type from joint name (e.g., "left_elbow" -> "elbow")
          const parts = joint.split('_');
          if (parts.length === 2) {
            joints.add(parts[1]);
          }
        }
      });
    }
    
    return Array.from(joints);
  };
  
  // Function to get display name for a joint
  const getJointDisplayName = (joint) => {
    if (joint === 'spine_top') return 'Spine Top';
    if (joint === 'spine_bottom') return 'Spine Bottom';
    return joint.charAt(0).toUpperCase() + joint.slice(1);
  };
  
  // Generate plot data for all selected joints
  const generatePlots = () => {
    const numJoints = selectedJoints.length;
    
    // Use heightPerPlot from state instead of fixed value
    // const height = numJoints * heightPerPlot;
    
    const plotData = [];
    const annotations = [];
    const shapes = [];
    
    // Index to keep track of which subplot we're on
    let plotIndex = 0;
    
    selectedJoints.forEach(joint => {
      // Handle regular joints (with left/right)
      if (['elbow', 'shoulder', 'hip', 'knee'].includes(joint)) {
        // Check if we have data for this joint type
        const hasRightData = masterData.angles && masterData.angles[`right_${joint}`];
        const hasLeftData = masterData.angles && masterData.angles[`left_${joint}`];
        
        if (!hasRightData && !hasLeftData) return; // Skip if no data
        
        // Calculate y-axis range for both left and right
        let yValues = [];
        ['left', 'right'].forEach(side => {
          const fullJoint = `${side}_${joint}`;
          if (masterData.angles && masterData.angles[fullJoint]) {
            yValues = yValues.concat(masterData.angles[fullJoint]);
          }
          if (learnerData.angles && learnerData.angles[fullJoint]) {
            yValues = yValues.concat(learnerData.angles[fullJoint]);
          }
        });
        
        yValues = yValues.filter(v => v !== null && v !== undefined);
        if (yValues.length === 0) return; // Skip if no valid data
        
        let minValue = Math.min(...yValues);
        let maxValue = Math.max(...yValues);
        
        // Add padding to the range
        const padding = Math.max((maxValue - minValue) * 0.2, 10);
        minValue = Math.max(0, minValue - padding);
        maxValue = maxValue + padding;
        
        // For each side (left/right)
        ['left', 'right'].forEach(side => {
          const fullJoint = `${side}_${joint}`;
          
          // Only add traces if this joint has data
          if (masterData.angles && masterData.angles[fullJoint]) {
            // For master data
            if (masterData.frames) {
              // If we have frame-by-frame data (not just key poses)
              plotData.push({
                x: masterData.frames,
                y: masterData.angles[fullJoint],
                type: 'scatter',
                mode: 'lines',
                name: `Master ${side}`,
                line: { 
                  color: side === 'left' ? 'rgba(0, 102, 255, 0.7)' : '#0066FF',
                  width: 2,
                  shape: 'spline' // Use spline for smooth curves
                },
                xaxis: `x`,
                yaxis: `y${plotIndex + 1}`,
                showlegend: false
              });
            } else if (masterData.keyPoseFrames) {
              // If we only have key pose data, connect the points with a smoothed line
              plotData.push({
                x: masterData.keyPoseFrames,
                y: masterData.angles[fullJoint],
                type: 'scatter',
                mode: 'lines+markers',
                name: `Master ${side}`,
                line: { 
                  color: side === 'left' ? 'rgba(0, 102, 255, 0.7)' : '#0066FF',
                  width: 2,
                  shape: 'spline' // Use spline for smooth curves
                },
                marker: {
                  color: side === 'left' ? 'rgba(0, 102, 255, 0.7)' : '#0066FF',
                  size: 8,
                  symbol: 'circle'
                },
                xaxis: `x`,
                yaxis: `y${plotIndex + 1}`,
                showlegend: false,
                hoverinfo: 'text',
                hovertext: masterData.keyPoseFrames.map((frame, i) => 
                  `Master ${side}: ${masterData.keyPoseNames?.[i] || `Pose ${i + 1}`}<br>Frame: ${frame}<br>Angle: ${masterData.angles[fullJoint][i].toFixed(1)}°`
                )
              });
            }
            
            // Add learner data if not in master-only mode
            if (comparisonMode !== 'masterOnly' && learnerData.angles && learnerData.angles[fullJoint]) {
              if (learnerData.frames) {
                // If we have frame-by-frame data
                plotData.push({
                  x: learnerData.frames,
                  y: learnerData.angles[fullJoint],
                  type: 'scatter',
                  mode: 'lines',
                  name: `Learner ${side}`,
                  line: { 
                    color: side === 'left' ? 'rgba(255, 51, 51, 0.7)' : '#FF3333',
                    width: 2,
                    dash: 'dash',
                    shape: 'spline' // Use spline for smooth curves
                  },
                  xaxis: `x`,
                  yaxis: `y${plotIndex + 1}`,
                  showlegend: false
                });
              } else if (learnerData.keyPoseFrames) {
                // If we only have key pose data
                plotData.push({
                  x: learnerData.keyPoseFrames,
                  y: learnerData.angles[fullJoint],
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: `Learner ${side}`,
                  line: { 
                    color: side === 'left' ? 'rgba(255, 51, 51, 0.7)' : '#FF3333',
                    width: 2,
                    dash: 'dash',
                    shape: 'spline' // Use spline for smooth curves
                  },
                  marker: {
                    color: side === 'left' ? 'rgba(255, 51, 51, 0.7)' : '#FF3333',
                    size: 8,
                    symbol: 'circle'
                  },
                  xaxis: `x`,
                  yaxis: `y${plotIndex + 1}`,
                  showlegend: false,
                  hoverinfo: 'text',
                  hovertext: learnerData.keyPoseFrames.map((frame, i) => 
                    `Learner ${side}: ${learnerData.keyPoseNames?.[i] || `Pose ${i + 1}`}<br>Frame: ${frame}<br>Angle: ${learnerData.angles[fullJoint][i].toFixed(1)}°`
                  )
                });
              }
            }
          }
        });
        
        // Add joint title annotation
        annotations.push({
          text: getJointDisplayName(joint),
          font: {
            size: 16,
            weight: 'bold'
          },
          x: 0,
          y: 1,
          xref: 'paper',
          yref: `y${plotIndex + 1} domain`,
          xanchor: 'left',
          yanchor: 'top',
          showarrow: false
        });
        
        // Add optimal range if available from right side (standard)
        const rightJoint = `right_${joint}`;
        if (masterData.rangeOfMotion && masterData.rangeOfMotion[rightJoint]) {
          const optimal = masterData.rangeOfMotion[rightJoint].optimal;
          
          annotations.push({
            text: `Optimal: ${optimal.toFixed(1)}°`,
            font: { size: 10 },
            x: 5,
            y: optimal,
            xref: 'x',
            yref: `y${plotIndex + 1}`,
            xanchor: 'left',
            showarrow: false,
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            borderpad: 2
          });
          
          // Add optimal range as a shaded rectangle 
          shapes.push({
            type: 'rect',
            x0: focusRange[0],
            x1: focusRange[1],
            y0: optimal * 0.9,
            y1: optimal * 1.1,
            xref: 'x',
            yref: `y${plotIndex + 1}`,
            fillcolor: 'rgba(0, 255, 200, 0.2)',
            line: { width: 0 }
          });
        }
        
        // Add problem areas
        if (comparisonMode !== 'masterOnly') {
          problemAreas.forEach(area => {
            const parts = area.joint.split('_');
            if (parts.length === 2 && parts[1] === joint) {
              shapes.push({
                type: 'rect',
                x0: area.frames[0],
                x1: area.frames[1],
                y0: minValue,
                y1: maxValue,
                xref: 'x',
                yref: `y${plotIndex + 1}`,
                fillcolor: 'rgba(255, 255, 0, 0.3)',
                line: { width: 0 }
              });
            }
          });
        }
        
        // Increment plot index for next joint
        plotIndex++;
      }
      // Handle spine_top and spine_bottom
      else if (joint === 'spine_top' || joint === 'spine_bottom') {
        // Skip if no data
        if (!masterData.angles || !masterData.angles[joint]) return;
        
        // Calculate y-axis range
        let yValues = [];
        if (masterData.angles[joint]) {
          yValues = yValues.concat(masterData.angles[joint]);
        }
        if (comparisonMode !== 'masterOnly' && learnerData.angles && learnerData.angles[joint]) {
          yValues = yValues.concat(learnerData.angles[joint]);
        }
        
        yValues = yValues.filter(v => v !== null && v !== undefined);
        if (yValues.length === 0) return; // Skip if no valid data

        let minValue = Math.min(...yValues);
        let maxValue = Math.max(...yValues);
        
        // Add padding to the range
        const padding = Math.max((maxValue - minValue) * 0.2, 10);
        minValue = Math.max(0, minValue - padding);
        maxValue = maxValue + padding;
        
        // Add master data
        if (masterData.frames) {
          // If we have frame-by-frame data
          plotData.push({
            x: masterData.frames,
            y: masterData.angles[joint],
            type: 'scatter',
            mode: 'lines',
            name: 'Master',
            line: { 
              color: '#0066FF',
              width: 2,
              shape: 'spline' // Use spline for smooth curves
            },
            xaxis: `x`,
            yaxis: `y${plotIndex + 1}`,
            showlegend: false
          });
        } else if (masterData.keyPoseFrames) {
          // If we only have key pose data
          plotData.push({
            x: masterData.keyPoseFrames,
            y: masterData.angles[joint],
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Master',
            line: { 
              color: '#0066FF',
              width: 2,
              shape: 'spline' // Use spline for smooth curves
            },
            marker: {
              color: '#0066FF',
              size: 8,
              symbol: 'circle'
            },
            xaxis: `x`,
            yaxis: `y${plotIndex + 1}`,
            showlegend: false,
            hoverinfo: 'text',
            hovertext: masterData.keyPoseFrames.map((frame, i) => 
              `Master: ${masterData.keyPoseNames?.[i] || `Pose ${i + 1}`}<br>Frame: ${frame}<br>Angle: ${masterData.angles[joint][i].toFixed(1)}°`
            )
          });
        }
        
        // Add learner data if not in master-only mode
        if (comparisonMode !== 'masterOnly' && learnerData.angles && learnerData.angles[joint]) {
          if (learnerData.frames) {
            // If we have frame-by-frame data
            plotData.push({
              x: learnerData.frames,
              y: learnerData.angles[joint],
              type: 'scatter',
              mode: 'lines',
              name: 'Learner',
              line: { 
                color: '#FF3333',
                width: 2,
                dash: 'dash',
                shape: 'spline' // Use spline for smooth curves
              },
              xaxis: `x`,
              yaxis: `y${plotIndex + 1}`,
              showlegend: false
            });
          } else if (learnerData.keyPoseFrames) {
            // If we only have key pose data
            plotData.push({
              x: learnerData.keyPoseFrames,
              y: learnerData.angles[joint],
              type: 'scatter',
              mode: 'lines+markers',
              name: 'Learner',
              line: { 
                color: '#FF3333',
                width: 2,
                dash: 'dash',
                shape: 'spline' // Use spline for smooth curves
              },
              marker: {
                color: '#FF3333',
                size: 8,
                symbol: 'circle'
              },
              xaxis: `x`,
              yaxis: `y${plotIndex + 1}`,
              showlegend: false,
              hoverinfo: 'text',
              hovertext: learnerData.keyPoseFrames.map((frame, i) => 
                `Learner: ${learnerData.keyPoseNames?.[i] || `Pose ${i + 1}`}<br>Frame: ${frame}<br>Angle: ${learnerData.angles[joint][i].toFixed(1)}°`
              )
            });
          }
        }
        
        // Add joint title annotation
        annotations.push({
          text: getJointDisplayName(joint),
          font: {
            size: 16,
            weight: 'bold'
          },
          x: 0,
          y: 1,
          xref: 'paper',
          yref: `y${plotIndex + 1} domain`,
          xanchor: 'left',
          yanchor: 'top',
          showarrow: false
        });
        
        // Add optimal range if available
        if (masterData.rangeOfMotion && masterData.rangeOfMotion[joint]) {
          const optimal = masterData.rangeOfMotion[joint].optimal;
          
          annotations.push({
            text: `Optimal: ${optimal.toFixed(1)}°`,
            font: { size: 10 },
            x: 5,
            y: optimal,
            xref: 'x',
            yref: `y${plotIndex + 1}`,
            xanchor: 'left',
            showarrow: false,
            bgcolor: 'rgba(255, 255, 255, 0.7)',
            borderpad: 2
          });
          
          // Add optimal range as a shaded rectangle 
          shapes.push({
            type: 'rect',
            x0: focusRange[0],
            x1: focusRange[1],
            y0: optimal * 0.9,
            y1: optimal * 1.1,
            xref: 'x',
            yref: `y${plotIndex + 1}`,
            fillcolor: 'rgba(0, 255, 200, 0.2)',
            line: { width: 0 }
          });
        }
        
        // Add problem areas
        if (comparisonMode !== 'masterOnly') {
          problemAreas.forEach(area => {
            if (area.joint === joint) {
              shapes.push({
                type: 'rect',
                x0: area.frames[0],
                x1: area.frames[1],
                y0: minValue,
                y1: maxValue,
                xref: 'x',
                yref: `y${plotIndex + 1}`,
                fillcolor: 'rgba(255, 255, 0, 0.3)',
                line: { width: 0 }
              });
            }
          });
        }
        
        // Increment plot index for next joint
        plotIndex++;
      }
    });
    
    // Get the actual number of plots we created (may be less than selectedJoints.length if some don't have data)
    const numPlots = plotIndex;
    
    const layout = {
      grid: {
        rows: numPlots,
        columns: 1,
        pattern: 'independent',
        roworder: 'top to bottom',
        rowgap: 0.1 // Add gap between plots
      },
      xaxis: {
        title: 'Frame',
        range: focusRange,
        showgrid: true,
        gridwidth: 1,
        gridcolor: 'rgba(200, 200, 200, 0.3)',
        tickmode: 'array',
        tickvals: Array.from({length: 11}, (_, i) => Math.round(focusRange[0] + (focusRange[1] - focusRange[0]) * i / 10))
      },
      // Use heightPerPlot from state instead of fixed value
      height: numPlots * heightPerPlot,
      margin: { l: 60, r: 20, t: 40, b: 60 },
      legend: { orientation: 'h', y: 1.05 },
      annotations: annotations,
      shapes: shapes,
      plot_bgcolor: 'rgba(250, 250, 250, 0.8)',
      paper_bgcolor: 'rgba(250, 250, 250, 0.8)'
    };
    
    // Add individual y-axes
    for (let i = 0; i < numPlots; i++) {
      // Calculate domain to add space between plots
      const domainHeight = 1 / numPlots * 0.9; // 90% of equal division
      const startY = (numPlots - i - 1) / numPlots;
      const endY = startY + domainHeight;
      
      layout[`yaxis${i + 1}`] = {
        title: 'Angle (°)',
        domain: [startY, endY],
        showgrid: true,
        gridwidth: 1,
        gridcolor: 'rgba(200, 200, 200, 0.3)'
      };
    }
    
    return { data: plotData, layout };
  };
  
  // Get plot data and layout
  const { data: plotData, layout } = generatePlots();
  
  // Handle joint selection
  const handleJointSelection = (joint) => {
    if (selectedJoints.includes(joint)) {
      setSelectedJoints(selectedJoints.filter(j => j !== joint));
    } else {
      setSelectedJoints([...selectedJoints, joint]);
    }
  };
  
  // Handle focus range change
  const handleRangeChange = (e) => {
    const value = parseInt(e.target.value);
    setFocusRange([0, value]);
  };
  
  // Handle height per plot change
  const handleHeightChange = (e) => {
    const value = parseInt(e.target.value);
    setHeightPerPlot(value);
  };
  
  return (
    <div className="joint-angle-chart-container">
      <div className="chart-header">
        <h2>Joint Angle Analysis</h2>
        <div className="chart-controls">
          <div className="chart-legend">
            <div className="legend-item">
              <div className="legend-line master-line"></div>
              <span>Master</span>
            </div>
            {comparisonMode !== 'masterOnly' && (
              <div className="legend-item">
                <div className="legend-line learner-line"></div>
                <span>Learner</span>
              </div>
            )}
            {comparisonMode !== 'masterOnly' && (
              <div className="legend-item">
                <div className="legend-area problem-area"></div>
                <span>Problem Area</span>
              </div>
            )}
            <div className="legend-item">
              <div className="legend-area optimal-area"></div>
              <span>Optimal Range</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="joint-selector">
        <h3>Select Joints to Display:</h3>
        <div className="joint-buttons">
          {getAvailableJoints().map(joint => (
            <button
              key={joint}
              className={`joint-button ${selectedJoints.includes(joint) ? 'selected' : ''}`}
              onClick={() => handleJointSelection(joint)}
            >
              {getJointDisplayName(joint)}
            </button>
          ))}
        </div>
      </div>
      
      <div className="chart-sliders">
        <div className="slider-container">
          {/* <h3>Focus Range:</h3> */}
          <div className="range-slider-container">
            <span><h4>Focus Range: Frame {focusRange[0]}</h4></span>
            <input 
              type="range"
              min="0"
              max="1200"
              value={focusRange[1]}
              onChange={handleRangeChange}
              className="range-slider"
            />
            <span>{focusRange[1]}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>

            <span><h4>Height Plot Range: {heightPerPlot}px</h4></span>
            <input 
              type="range"
              min="150"
              max="600"
              value={heightPerPlot}
              onChange={handleHeightChange}
              className="range-slider"
            />
            <span>per plot</span>
          </div>
        </div>
      </div>
      
      <div className="plot-container">
        <Plot 
          data={plotData} 
          layout={layout} 
          config={{ responsive: true }} 
          className={`chart-plot chart-mode-${comparisonMode}`}
        />
      </div>
      
      {problemAreas.length > 0 && comparisonMode !== 'masterOnly' && (
        <div className="problem-areas-section">
          <h3>Areas Needing Improvement</h3>
          <div className="problem-areas-list">
            {problemAreas.map((area, index) => (
              <div key={index} className="problem-area-item">
                <span>
                  {area.joint === 'spine_top' ? 'Spine Top' : 
                   area.joint === 'spine_bottom' ? 'Spine Bottom' : 
                   `${area.joint.split('_')[0]} ${area.joint.split('_')[1]}`}: 
                  Frames {area.frames[0]}-{area.frames[1]}
                </span>
                <span className="diff-value">{area.diff}° diff</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Range of Motion Analysis */}
      {!compact && masterData.rangeOfMotion && (
        <div className="range-of-motion">
          <h3>Range of Motion Analysis</h3>
          <table>
            <thead>
              <tr>
                <th>Joint</th>
                <th>Min (°)</th>
                <th>Max (°)</th>
                <th>Optimal (°)</th>
                {comparisonMode !== 'masterOnly' && <th>Diff</th>}
              </tr>
            </thead>
            <tbody>
              {Object.keys(masterData.rangeOfMotion)
                .filter(joint => {
                  // Only include joints that are in the selected list
                  if (joint === 'spine_top' || joint === 'spine_bottom') {
                    return selectedJoints.includes(joint);
                  } else {
                    const parts = joint.split('_');
                    return parts.length === 2 && selectedJoints.includes(parts[1]);
                  }
                })
                .map(joint => {
                  const masterROM = masterData.rangeOfMotion[joint];
                  const learnerROM = learnerData.rangeOfMotion && learnerData.rangeOfMotion[joint];
                  const optimalDiff = learnerROM ? (learnerROM.optimal - masterROM.optimal).toFixed(1) : '-';
                  
                  // Format joint name for display
                  let jointDisplayName;
                  if (joint === 'spine_top') {
                    jointDisplayName = 'Spine Top';
                  } else if (joint === 'spine_bottom') {
                    jointDisplayName = 'Spine Bottom';
                  } else {
                    const parts = joint.split('_');
                    jointDisplayName = `${parts[0]} ${getJointDisplayName(parts[1])}`;
                  }
                  
                  return (
                    <tr key={joint}>
                      <td>{jointDisplayName}</td>
                      <td>{masterROM.min.toFixed(1)}</td>
                      <td>{masterROM.max.toFixed(1)}</td>
                      <td>{masterROM.optimal.toFixed(1)}</td>
                      {comparisonMode !== 'masterOnly' && (
                        <td className={optimalDiff > 0 ? 'positive-diff' : optimalDiff < 0 ? 'negative-diff' : ''}>
                          {optimalDiff}
                        </td>
                      )}
                    </tr>
                  );
                })
              }
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default JointAngleChart;