package collab.autodoc;

public class ConfigObject {

    private String url;
    private String author;
    private String project;
    private String version;
    private String date;
    private String commit;
    private String branch;
    private String feature;

    private String defaultConfigLocation ="./";

    public ConfigObject() {

    }

    private ConfigObject(String url, String author, String project, String version, String date, String commit, String branch, String feature) {
        this.url = url;
        this.author = author;
        this.project = project;
        this.version = version;
        this.date = date;
        this.commit = commit;
        this.branch = branch;
        this.feature = feature;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }
}
