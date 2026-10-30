import { Trash2, Upload } from "lucide-react";
import { HelpButton, HelpItem } from "@/components/HelpButton";
import { LedgerBadge } from "@/components/ledger/LedgerBadge";
import { StatusBadge } from "@/components/ledger/StatusBadge";
import { ThemeToggle } from "@/components/ThemeToggle";

export function LedgerToolbar() {
	return (
		<>
			<ThemeToggle />
			<HelpButton title="Ledger" ariaLabel="Ledger help">
				<HelpItem
					term={
						<>
							<Upload className="inline h-4 w-4 align-text-bottom" /> Upload
							Ledger
						</>
					}
				>
					import a ModL ledger as a SQLite database. It is read in your browser
					and never uploaded.
				</HelpItem>
				<HelpItem
					term={
						<>
							<Trash2 className="inline h-4 w-4 align-text-bottom" /> Remove
							ledger
						</>
					}
				>
					close the ledger and clear its tables, searches and queries.
				</HelpItem>
				<HelpItem term="Raw Tables">
					browse each ledger table with search and pagination.
				</HelpItem>
				<HelpItem term="Explore">
					search the whole ledger at once, by label, kind, status, URI, serial
					or instance.
				</HelpItem>
				<HelpItem term="Query">
					run a predefined query or write your own read-only SQL. The database
					schema is listed here while this view is open.
				</HelpItem>
				<HelpItem
					term={
						<span className="flex items-center gap-2">
							<LedgerBadge tone="active">8</LedgerBadge>
							<span className="text-muted-foreground text-sm">9</span>
						</span>
					}
				>
					in the table summary above: active records, then the total.
				</HelpItem>
				<HelpItem
					term={
						<span className="flex flex-wrap items-center gap-1">
							<StatusBadge status="ACTIVE" />
							<StatusBadge status="SUPERSEDED" />
							<StatusBadge status="REMOVED" />
						</span>
					}
				>
					a record's status, shown wherever a status column appears.
				</HelpItem>
				<HelpItem term="Highlighted row">
					the record currently open in the details pane on the right.
				</HelpItem>
			</HelpButton>
		</>
	);
}
