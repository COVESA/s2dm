import type { ClientModule } from "@docusaurus/types";

const LINKED_HEADING_ATTRIBUTE = "data-linked-heading";

/**
 * Mark the element the URL's `#anchor` points at, so CSS can highlight it.
 *
 * CSS `:target` is not enough: in-app navigation changes the URL without updating it.
 */
const markLinkedHeading: ClientModule = {
	onRouteDidUpdate({ location }) {
		const markedElements = document.querySelectorAll(
			`[${LINKED_HEADING_ATTRIBUTE}]`,
		);
		for (const markedElement of markedElements) {
			markedElement.removeAttribute(LINKED_HEADING_ATTRIBUTE);
		}
		if (!location.hash) {
			return;
		}
		const anchorId = decodeURIComponent(location.hash.slice(1));
		document
			.getElementById(anchorId)
			?.setAttribute(LINKED_HEADING_ATTRIBUTE, "");
	},
};

export default markLinkedHeading;
