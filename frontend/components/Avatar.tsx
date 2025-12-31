import React, { useEffect } from 'react';
import { useRive, useStateMachineInput } from '@rive-app/react-canvas';

interface AvatarProps {
  className?: string;
  style?: React.CSSProperties;
  isTalking?: boolean;
}

export const Avatar: React.FC<AvatarProps> = ({ className, style, isTalking = false }) => {
  const { rive, RiveComponent } = useRive({
    src: '/New.riv', // Path to the Rive file in public folder
    stateMachines: 'avatar', // State machine name from avatar1.html
    autoplay: true,
    onLoad: () => {
      console.log('Avatar loaded successfully');
      // Set initial state to false (idle) - matching avatar1.html behavior
      if (rive) {
        const inputs = rive.stateMachineInputs('avatar');
        const takingInput = inputs?.find(input => input.name === 'Taking');
        if (takingInput) {
          takingInput.value = false;
          console.log('✅ Set Taking to false (idle state)');
        }
      }
    },
    onLoadError: (error) => {
      console.error('Avatar load error:', error);
      console.log('This is likely due to WASM loading issues. The avatar will still work but may not animate properly.');
    }
  });

  // Get the "Taking" boolean input
  const takingInput = useStateMachineInput(rive, 'avatar', 'Taking', false);

  // Update the Taking input when isTalking changes
  useEffect(() => {
    console.log(`🎭 Avatar isTalking prop changed to: ${isTalking}`);
    if (takingInput) {
      takingInput.value = isTalking;
      console.log(`🎭 Avatar Taking state updated to: ${isTalking}`);
    } else {
      console.log(`🎭 Avatar takingInput not available yet`);
    }
  }, [takingInput, isTalking]);

  return (
    <div className={className} style={style}>
      <RiveComponent 
        style={{ 
          width: '100%', 
          height: '100%',
          borderRadius: '15px',
          overflow: 'hidden'
        }}
      />
    </div>
  );
};
