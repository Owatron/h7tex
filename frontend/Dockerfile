# Use an official Node runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package.json ./
# If you use package-lock.json, uncomment the next line
# COPY package-lock.json ./

# Install app dependencies
RUN npm install

# Copy the rest of the application's source code from the host to the container's /app directory
COPY . .

# The app runs on port 3000, so we expose it
EXPOSE 3000

# The command to start the app
CMD ["npm", "start"]

