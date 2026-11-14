# Deployment analysis

- Deployment URL: https://logistics-platform-t77a.onrender.com/
- Inspection date: 13 November 2026.
- The initial request showed Render's cold-start/wake-up interstitial and a transient 503; a subsequent load rendered the Meridian application successfully.
- The rendered Overview displayed the dark-blue sidebar/header, Meridian identity, navigation for Overview, Route optimizer, Comparison Lab, Network Manager, Analytics and Algorithms Explained; scenario and metric selectors; a 25-location/102-route Standard network; and recommendation badges. A screenshot was visually inspected in the browser.
- After the initial cold start, the Comparison Lab, Network Manager and Algorithms Explained views were also opened and inspected. Analytics was revisited after loading completed; the rendered charts showed weekly spend by mode (air $8.7M, rail $164K, road $826K, sea $431K), average delivery time (14.5 h, 33.6 h, 25.6 h, 276.4 h respectively), and cost per km ($6.87, $1.29, $1.91, $0.47 respectively). Route-efficiency and connectivity sections were present. These are synthetic application analytics, not operational shipment data.
- No production data was edited. Interaction was limited to reading/rendering the application, not creating, deleting or changing network data.
- The deployed site was not treated as identical to the repository solely by assumption. Detailed source claims are attributed to the local repository; deployment-specific claims are limited to what was visibly observed.
- The cold-start interstitial means availability may vary. Other interactive actions that would create route-run history or mutate records were not used for deployment testing.

## Observed implementation difference

The deployed Algorithms Explained view describes Bellman–Ford in terms of “streaming edge lists.” The local repository implementation relaxes its in-memory edge list; no streaming or distributed edge-processing mechanism was found in the source reviewed for this report. The report therefore describes the repository behavior and does not claim streaming execution. This wording difference was recorded as a deployment/source discrepancy, not resolved by assumption.

## Accuracy boundary

The locally rendered app is served from the repository implementation, using a separate report-output SQLite database. It is suitable for genuine screenshots of current local UI behavior, but it does not prove that the deployed build is byte-for-byte identical. The online URL is included in the report/User Manual with the cold-start caveat. The User Manual identifies local implementation behavior where deployment equivalence was not established.
