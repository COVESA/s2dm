import { KeyRound, Trash2, X } from "lucide-react";
import { HelpButton, HelpItem } from "@/components/HelpButton";

export function ReleasesHelpButton() {
	return (
		<HelpButton title={"Releases"} ariaLabel={"Releases help"} size={"icon"}>
			<HelpItem term={"Load Releases"}>
				list the releases of the GitHub repository at the URL. Private
				repositories use the stored identities. Cancel stops a running load.
			</HelpItem>
			<HelpItem
				term={
					<>
						<KeyRound className={"inline h-4 w-4 align-text-bottom"} /> Manage
						identities
					</>
				}
			>
				import, add, edit or remove the identities (host and scope) used to
				fetch private repositories. They are the same identities as in Manage
				Dependencies.
			</HelpItem>
			<HelpItem
				term={
					<>
						<Trash2 className={"inline h-4 w-4 align-text-bottom"} /> Remove
						repository
					</>
				}
			>
				clear the loaded releases. Exploring a release stops first.
			</HelpItem>
			<HelpItem term={"Releases section"}>
				lists the loaded releases. Click a release to explore it. Grayed-out
				releases have no supported schema asset.
			</HelpItem>
			<HelpItem
				term={
					<>
						<X className={"inline h-4 w-4 align-text-bottom"} /> Stop exploring
						releases
					</>
				}
			>
				ends the exploration. The Schema workspace is disabled while a release
				is explored.
			</HelpItem>
		</HelpButton>
	);
}
