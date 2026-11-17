import { Button } from "@shared-ui/components/button";
import { Input } from "@shared-ui/components/input";
import { useId, useState } from "react";
import { Label } from "@/components/ui/label";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	cancelReleasePageLoad,
	fetchReleasePage,
	selectReleases,
	setRepositoryInput,
} from "@/store/releases/releasesSlice";
import { getUrlError } from "@/utils/validation";

export function ReleaseRepositoryForm() {
	const dispatch = useAppDispatch();
	const releases = useAppSelector(selectReleases);
	const repositoryInputId = useId();

	const [urlError, setUrlError] = useState("");

	const repositoryInput = releases.repositoryInput;
	const isLoadingPage = releases.isLoadingPage;

	const handleLoadReleases = () => {
		const repository = repositoryInput.trim();
		const repositoryError = getUrlError(repository);
		if (repositoryError) {
			setUrlError(repositoryError);
			return;
		}

		const fetchAction = fetchReleasePage({ repository, page: 1 });
		dispatch(fetchAction);
	};

	const handleCancelLoad = () => {
		const cancelAction = cancelReleasePageLoad();
		dispatch(cancelAction);
	};

	const handleRepositoryInputChange = (value: string) => {
		const inputAction = setRepositoryInput(value);
		dispatch(inputAction);
		setUrlError("");
	};

	return (
		<div className={"grid gap-2 px-2 pb-2"}>
			<Label htmlFor={repositoryInputId}>Repository URL</Label>
			<div className={"flex gap-2"}>
				<Input
					id={repositoryInputId}
					placeholder={"https://github.com/owner/repository"}
					value={repositoryInput}
					onChange={(event) => {
						handleRepositoryInputChange(event.target.value);
					}}
					onKeyDown={(event) => {
						if (event.key === "Enter") {
							handleLoadReleases();
						}
					}}
				/>
				<Button
					type={"button"}
					variant={"outline"}
					onClick={handleLoadReleases}
					loading={isLoadingPage}
				>
					Load Releases
				</Button>
				{isLoadingPage && (
					<Button
						type={"button"}
						variant={"outline"}
						onClick={handleCancelLoad}
					>
						Cancel
					</Button>
				)}
			</div>
			{urlError && <p className={"text-sm text-destructive"}>{urlError}</p>}
		</div>
	);
}
