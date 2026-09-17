import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import CustomerDetails from "./pages/CustomerDetails";
import NewCustomer from "./pages/NewCustomer";
import RiskIntelligence from "./pages/RiskIntelligence";
import RetentionCenter from "./pages/RetentionCenter";
import SimulatorPage from "./pages/SimulatorPage";
import Assistant from "./pages/Assistant";
import Reports from "./pages/Reports";
import ModelPerformance from "./pages/ModelPerformance";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/customers/:customerIndex" element={<CustomerDetails />} />
          <Route path="/new-customer" element={<NewCustomer />} />
          <Route path="/risk-intelligence" element={<RiskIntelligence />} />
          <Route path="/retention" element={<RetentionCenter />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="/model-performance" element={<ModelPerformance />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
