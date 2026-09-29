import Link from "@docusaurus/Link";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Heading from "@theme/Heading";
import Layout from "@theme/Layout";
import type { ReactNode } from "react";
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
					<Link
						className="button button--primary button--lg"
						to="/docs/elements"
					>
						Docs
					</Link>
					<Link
						className="button button--secondary button--lg"
						to="/visualizer"
					>
						Visualizer
					</Link>
					<Link className="button button--secondary button--lg" to="/insights">
						Insights
					</Link>
					<Link className="button button--secondary button--lg" to="/ledger">
						Ledger
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
					<li>Insights generated from the composed schema</li>
					<li>
						Ledger read in your browser with{" "}
						<a
							href="https://sql.js.org"
							target="_blank"
							rel="noopener noreferrer"
						>
							sql.js
						</a>
					</li>
				</ul>
			</main>
		</Layout>
	);
}
