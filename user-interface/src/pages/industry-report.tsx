import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";
import { useEffect, useReducer, useState } from "react";
import BaseAppLayout from "../components/base-app-layout";
import styles from "../styles/tckrnews-ui.module.scss";
import { Button, Container, Header, Input, SpaceBetween, Spinner, Textarea } from "@cloudscape-design/components";

export default function IndustryReportPage() {
  const [industry, setIndustry] = useState("");
  const [region, setRegion] = useState("global");
  const [horizon, setHorizon] = useState("next 12 months");
  const [client, setClient] = useState<WebSocket>();
  const [report, setReport] = useState<string>("");
  const [showSpinner, setShowSpinner] = useState<boolean>(false);
  const [socketReady, setSocketReady] = useState<boolean>(true);
  const [closed, forceClose] = useReducer(() => true, false);

  const cnf = Amplify.getConfig();

  const initializeClient = async () => {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    const apiClient = new WebSocket(`${cnf?.API?.REST?.WebSocketApi?.endpoint}?idToken=${idToken}`);

    apiClient.onopen = () => setSocketReady(false);
    apiClient.onerror = () => setSocketReady(true);
    apiClient.onclose = () => {
      setSocketReady(true);
      if (!closed) setTimeout(async () => await initializeClient());
    };
    apiClient.onmessage = async (message: any) => {
      try {
        const payload = JSON.parse(message.data);
        const body = payload?.body;
        if (body?.industry_report) {
          setReport(JSON.stringify(body.industry_report, null, 2));
          setShowSpinner(false);
        }
      } catch (e) {
        console.error(e);
      }
    };

    setClient(apiClient);
  };

  const runReport = async () => {
    if (!client) return;
    setReport("");
    setShowSpinner(true);
    client.send(
      JSON.stringify({
        action: "getIndustryReport",
        industry,
        region,
        time_horizon: horizon,
      })
    );
  };

  useEffect(() => {
    initializeClient();
    return () => {
      if (client) {
        forceClose();
        client.close();
      }
    };
  }, []);

  return (
    <BaseAppLayout
      content={
        <div className={styles.news_container}>
          <SpaceBetween size="s">
            <div className={styles.input_container}>
              <Input placeholder="Industry (e.g., Semiconductors)" value={industry} onChange={({ detail }) => setIndustry(detail.value)} />
            </div>
            <div className={styles.input_container}>
              <Input placeholder="Region (optional)" value={region} onChange={({ detail }) => setRegion(detail.value)} />
            </div>
            <div className={styles.input_container}>
              <Input placeholder="Time horizon" value={horizon} onChange={({ detail }) => setHorizon(detail.value)} />
            </div>
            <div>
              <Button variant="primary" onClick={runReport} disabled={socketReady || !industry}>Generate Industry Report</Button>
            </div>
            <div style={showSpinner ? {} : { display: 'none' }}>
              <Spinner size="large" /> Generating report...
            </div>
            <Container header={<Header variant="h2">Report (JSON)</Header>}>
              <Textarea value={report} rows={24} onChange={() => {}} readOnly />
            </Container>
          </SpaceBetween>
        </div>
      }
    />
  );
}

