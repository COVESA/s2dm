import type { ReactNode } from "react";
import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";
import Heading from "@theme/Heading";
import styles from "./index.module.css";

export default function Home(): ReactNode {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout title="Home" description="CCS Domain Data Model documentation">
      <main className={styles.hero}>
        <Heading as="h1">{siteConfig.title}</Heading>
        <p className={styles.subtitle}>
          Data model following the{" "}
          <a
            href="https://github.com/COVESA/s2dm"
            target="_blank"
            rel="noopener noreferrer"
          >
            s2dm approach
          </a>{" "}
          by{" "}
          <a
            href="https://covesa.global"
            target="_blank"
            rel="noopener noreferrer"
          >
            COVESA
          </a>
          .
        </p>
        <div className={styles.buttons}>
          <Link className="button button--primary button--lg" to="/docs/elements">
            Docs
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/visualizer"
          >
            Visualizer
          </Link>
        </div>
        <ul className={styles.toolList}>
          <li>
            Docs built with{" "}
            <a
              href="https://graphql-markdown.dev"
              target="_blank"
              rel="noopener noreferrer"
            >
              GraphQL Markdown
            </a>
          </li>
          <li>
            Visualizer powered by{" "}
            <a
              href="https://github.com/APIs-guru/graphql-voyager"
              target="_blank"
              rel="noopener noreferrer"
            >
              GraphQL Voyager
            </a>
          </li>
        </ul>
      </main>
    </Layout>
  );
}
