import React from 'react';

const ElementCounts = ({ elementCounts }) => {
  return (
    <div className="element-counts">
      <h3>Elements Found:</h3>
      <ul>
        {Object.entries(elementCounts).map(([element, count]) => (
          <li key={element}>{element}: {count}</li>
        ))}
      </ul>
    </div>
  );
};

export default ElementCounts;
