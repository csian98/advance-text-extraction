import "./App.css";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { useImmerReducer } from "use-immer";
import "./leafletIconFix";

type Action = { type: "SET_WELLS"; payload: [] };

type Well = {
  LATITUDE: string;
  LONGITUDE: string;
  WELL_NAME?: string;
  WELL_STATUS?: string;
  WELL_TYPE?: string;
  API_NO?: string;
  OPERATOR?: string;
  CLOSEST_CITY?: string;
  OIL_PRODUCED?: string;
  GAS_PRODUCED?: string;
};

function App() {
  // const [count, setCount] = useState(0);
  console.log("App component rendered");

  const [wells, dispatch] = useImmerReducer((_, action: Action) => {
    switch (action.type) {
      case "SET_WELLS":
        return action.payload;
      default:
        break;
    }
  }, []);

  useEffect(() => {
    console.log("Fetching wells data...");
    fetch("http://localhost:5000/api/wells")
      .then((response) => response.json())
      .then((data) => {
        console.log("Wells data received:", data);
        dispatch({ type: "SET_WELLS", payload: data });
      })
      .catch((error) => {
        console.error("Error fetching wells data:", error);
      });
  }, [dispatch]);

  return (
    <>
      <div className="h-screen w-full">
        <MapContainer
          center={[48.21, -103.6]}
          zoom={11}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {wells.map((well: Well, index) => (
            <Marker
              key={index}
              position={[Number(well.LATITUDE), Number(well.LONGITUDE)]}
            >
              <Popup>
                <div>
                  <strong>Well Name:</strong> {well.WELL_NAME ?? "Unknown"}
                  <br />
                  <strong>Status:</strong> {well.WELL_STATUS ?? "Unknown"}
                  <br />
                  <strong>Type:</strong> {well.WELL_TYPE ?? "Unknown"}
                  <br />
                  <strong>API No:</strong> {well.API_NO ?? "Unknown"}
                  <br />
                  <strong>Operator:</strong> {well.OPERATOR ?? "Unknown"}
                  <br />
                  <strong>Closest City:</strong>{" "}
                  {well.CLOSEST_CITY ?? "Unknown"}
                  <br />
                  <strong>Oil Produced:</strong>{" "}
                  {well.OIL_PRODUCED ?? "Unknown"}
                  <br />
                  <strong>Gas Produced:</strong>{" "}
                  {well.GAS_PRODUCED ?? "Unknown"}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </>
  );
}

export default App;
