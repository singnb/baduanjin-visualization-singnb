# Baduanjin Visualization - Frontend

> A React-based frontend application for visualizing Baduanjin exercise data and analytics.

## Prerequisites

Before you begin, ensure you have the following installed on your system:

| Tool        | Version                 | Download Link                       |
| ----------- | ----------------------- | ----------------------------------- |
| **Node.js** | 14.0+                   | [nodejs.org](https://nodejs.org/)   |
| **npm**     | (included with Node.js) | -                                   |
| **Git**     | Latest                  | [git-scm.com](https://git-scm.com/) |

### Verify Installation

```bash
node --version
npm --version
git --version
```

## Getting Started

### 1. Create the React Application

Open PowerShell, Command Prompt, or Terminal:

#### Navigate to your desired directory

```bash
cd `path to project folder`
```

#### Create a new React application

```bash
npx create-react-app baduanjin-visualization
```

> **What this does:**
>
> - Uses `npx` to run the package without installing it globally
> - Sets up a new React project with `create-react-app`
> - Creates a project directory named `baduanjin-visualization`

#### Navigate into your project directory

```bash
cd baduanjin-visualization
```

### 2. Install Dependencies

Install the required packages for the application:

```bash
npm install axios react-plotly.js react-router-dom
```

#### Package Descriptions

| Package            | Purpose                       |
| ------------------ | ----------------------------- |
| `axios`            | HTTP client for API requests  |
| `react-plotly.js`  | Data visualization library    |
| `react-router-dom` | Client-side routing for React |

## Project Structure

After setup, your project structure will look like this:

```
baduanjin-visualization/
├── node_modules/          	# All installed packages (auto-generated)
├── public/               		# Static files served by the web server
│   ├── index.html       		# Main HTML template
│   ├── favicon.ico      		# Website icon
│   └── manifest.json    		# Web app manifest
├── src/                 		# Source code directory
│   ├── App.js          		# Main React component
│   ├── App.css         		# Main stylesheet
│   ├── index.js        		# Application entry point
│   ├── index.css       		# Global styles
│   └── auth/     			   # Folder for login and authentication functionality
│   └── components/     		# with five specialized subfolders
│   │   └── Analysis/     	   # Views for displaying Baduanjin analysis results
│   │   └── Charts/     		# Plotly-based chart visualizations
│   │   └── Layout/     		# UI components for Learner-Master account interfaces
│   │   └── Relationships/    # Components for managing Learner-Master relationships
│   │   └── UserAgreement/    # User agreement form components
│   |── services/     		   # Data loading and API service functions
│   |── __tests__/            # Testing folder
│   |     └── auth/           # Authication unit testing folder
├── package.json         		# Project configuration and dependencies
├── package-lock.json    		# Dependency lock file
└── README.md           		# Project documentation
```

## Development

### Start the Development Server for localhost

```bash
npm start
```

**This will:**

- Start the development server on `http://localhost:3000`
- Automatically open your browser
- Enable hot reloading (changes appear instantly)

### Available Scripts

| Command         | Description                      |
| --------------- | -------------------------------- |
| `npm start`     | Starts development server        |
| `npm run build` | Creates production build         |
| `npm test`      | Runs test suite                  |
| `npm run eject` | Ejects from CRA (irreversible)   |

### Unit Testing
- Clear Jest cache before the test
```bash
# Clear the cache
npm test -- --clearCache

# Individual unit testing
npm test -- --testPathPattern={unittestfilename}
npm test -- --testPathPattern=PiStatusPanel.test.js 

# Components testing stdout and stderr
npm run test:auth > src/__tests__/reports/authentication-test-results.txt 2>&1
npm run test:services > src/__tests__/reports/services-test-results.txt 2>&1
npm run test:analysis > src/__tests__/reports/analysis-test-results.txt 2>&1
npm run test:charts > src/__tests__/reports/chart-test-results.txt 2>&1
npm run test:layout > src/__tests__/reports/layout-test-results.txt 2>&1
npm run test:pilive > src/__tests__/reports/pilive-test-results.txt 2>&1

# All unit testing stdout and stderr
npm run test:unit > src/__tests__/reports/unit-test-results.txt 2>&1
```

## Development Workflow

1. **Start the development server**

   ```bash
   npm start
   ```

2. **Make changes** to files in the `src/` directory

3. **View changes** automatically in your browser at `http://localhost:3000`

4. **Test your application**

   ```bash
   npm test
   ```

5. **Build for production**

   ```bash
   npm run build
   ```

## Additional Resources

| Resource                | Link                                                         |
| ----------------------- | ------------------------------------------------------------ |
| React Documentation     | [reactjs.org/docs](https://legacy.reactjs.org/docs/getting-started.html) |
| Create React App Docs   | [create-react-app.dev](https://create-react-app.dev/docs/getting-started) |
| React Router            | [reactrouter.com](https://reactrouter.com/)                  |
| Plotly.js Documentation | [plotly.com/javascript](https://plotly.com/javascript/)      |
| Axios Documentation     | [axios-http.com](https://axios-http.com/)                    |

## License
```bash
This project is licensed under the MIT License.
```

